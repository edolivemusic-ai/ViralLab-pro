import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
from moviepy.config import change_settings
import tempfile
import os
import json
import time
import concurrent.futures
import PIL.Image
import numpy as np
import re

# --- PATCH COMPATIBILITÀ PIL ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURAZIONE IMAGEMAGICK (Per Linux/Streamlit Cloud) ---
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

# --- CONFIGURAZIONE STREAMLIT ---
st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .main { background-color: #0f1116; color: white; }
    .stButton>button {
        background: linear-gradient(90deg, #00f2ea, #FF0050);
        color: white; border: none; border-radius: 10px; height: 55px; width: 100%; font-weight: bold;
    }
    .stExpander { background-color: #1e2129; border-radius: 10px; }
    .error-box { background-color: #441111; padding: 10px; border-radius: 5px; border-left: 5px solid red; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Highlight Editor ☀️")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

# Configurazione Google AI
genai.configure(api_key=api_key)

# --- COSTANTI ---
MAX_CLIPS = 10
MODEL_ID = "gemini-1.5-flash"  # Modello ottimizzato per video e JSON

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)}
}

# ─────────────────────────────────────────
# FUNZIONI DI ANALISI E LOGICA
# ─────────────────────────────────────────

def cleanup_temp_files(paths):
    """Rimuove file temporanei in sicurezza."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except:
            pass

def get_audio_peak(video_path, start_hint=0.0):
    """Trova il picco di volume vicino al suggerimento AI."""
    try:
        v = mp.VideoFileClip(video_path)
        if v.audio is None:
            v.close()
            return start_hint
        
        duration = v.duration
        step = 0.5
        timestamps = np.arange(0, max(0, duration - step), step)
        rms_values = []
        
        for t in timestamps:
            chunk = v.audio.subclip(t, min(t + step, duration))
            samples = chunk.to_soundarray(fps=22050)
            rms = np.sqrt(np.mean(samples ** 2))
            rms_values.append(rms)
        v.close()

        # Cerca picco in finestra di 10 secondi
        window_start = max(0, start_hint - 5)
        window_end = min(duration, start_hint + 5)
        idx_start = int(window_start / step)
        idx_end = int(window_end / step)

        window_rms = rms_values[idx_start:idx_end]
        if window_rms:
            peak_idx = idx_start + int(np.argmax(window_rms))
            return float(timestamps[peak_idx])
        return start_hint
    except:
        return start_hint

def scan_single_video(f, cat):
    """Analizza un video con Gemini 1.5 Flash."""
    p = ""
    v_ai = None
    try:
        # 1. Salva localmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        # 2. Carica su Google AI Studio
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(2)
        
        # 3. Richiesta AI
        model = genai.GenerativeModel(MODEL_ID)
        prompt = (f"Analizza questo video di {cat}. Trova il picco energetico "
                  "(es. un drop musicale, un brindisi o un momento emozionante). "
                  "Rispondi ESCLUSIVAMENTE con un oggetto JSON: "
                  "{\"start\": float, \"reason\": string}")
        
        r = model.generate_content(
            [v_ai, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 4. Parsing Risposta
        d = json.loads(r.text)
        ai_start = float(d.get('start', 0))
        
        # 5. Fine-tuning audio
        audio_peak = get_audio_peak(p, start_hint=ai_start)
        
        d.update({
            'start_ai': ai_start, 
            'start': audio_peak, 
            'path': p, 
            'name': f.name, 
            'include': True
        })
        return d
    except Exception as err:
        if p: cleanup_temp_files([p])
        return {'error': str(err), 'name': f.name}
    finally:
        if v_ai:
            try: genai.delete_file(v_ai.name)
            except: pass

def render_sizzle(data_to_use, plat, ctype, clip_duration, audio_path):
    """Genera il video finale montato."""
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data_to_use:
            if not os.path.exists(d['path']): continue
            v = mp.VideoFileClip(d['path'])
            start = float(d['start'])
            end = min(start + float(clip_duration), v.duration)
            
            # Subclip e adattamento formato
            clip = v.subclip(start, end).resize(height=th)
            if clip.w > tw:
                clip = clip.crop(x_center=clip.w/2, width=tw)
            
            clips.append(clip.fadein(0.2).fadeout(0.2))
        
        if not clips: return None

        final_video = mp.concatenate_videoclips(clips, method="compose")
        
        # Mix audio background
        if audio_path and os.path.exists(audio_path):
            bg_audio = mp.AudioFileClip(audio_path).subclip(0, final_video.duration).audio_fadeout(2)
            if final_video.audio:
                final_video.audio = mp.CompositeAudioClip([
                    bg_audio.volumex(0.7), 
                    final_video.audio.volumex(0.3)
                ])
            else:
                final_video.audio = bg_audio
        
        out_name = f"sizzle_{int(time.time())}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        
        for c in clips: c.close()
        return out_name
    except Exception as e:
        st.error(f"Errore rendering: {e}")
        return None

# ─────────────────────────────────────────
# INTERFACCIA STREAMLIT
# ─────────────────────────────────────────

with st.sidebar:
    st.header("📍 Puglia Config")
    cat = st.selectbox("Tipo Evento", ["DJ Set", "Live Music", "Wedding Puglia", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    clip_duration = st.slider("Durata clip (sec)", 1.0, 5.0, 2.5)
    st.divider()
    audio_upload = st.file_uploader("Audio Soundtrack (MP3)", type=["mp3", "wav"])
    st.divider()
    files = st.file_uploader("📤 Carica Video (Max 10)", type=["mp4", "mov"], accept_multiple_files=True)

if files:
    # --- STEP 1: ANALISI ---
    if st.button("🔎 1. ANALIZZA HIGHLIGHTS AI"):
        results = []
        with st.status("🛸 AI sta analizzando i video (Gemini 1.5 Flash)...") as status:
            # max_workers=2 per gestire la RAM limitata di Streamlit Cloud
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(scan_single_video, f, cat) for f in files[:MAX_CLIPS]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res:
                        st.write(f"❌ **{res['name']}**: {res['error']}")
                    else:
                        st.write(f"✅ **{re
