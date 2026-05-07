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
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Highlight Editor ☀️")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- COSTANTI ---
MAX_CLIPS = 10
MODEL_ID = "gemini-1.5-flash"

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)}
}

# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def cleanup_temp_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except:
            pass

def get_audio_peak(video_path, start_hint=0.0):
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
    p = ""
    v_ai = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(2)
        
        model = genai.GenerativeModel(MODEL_ID)
        prompt = (f"Analizza questo video di {cat}. Trova il picco energetico. "
                  "Rispondi ESCLUSIVAMENTE con un oggetto JSON: "
                  "{\"start\": float, \"reason\": string}")
        
        r = model.generate_content(
            [v_ai, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        d = json.loads(r.text)
        ai_start = float(d.get('start', 0))
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
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data_to_use:
            if not os.path.exists(d['path']): continue
            v = mp.VideoFileClip(d['path'])
            start = float(d['start'])
            end = min(start + float(clip_duration), v.duration)
            
            clip = v.subclip(start, end).resize(height=th)
            if clip.w > tw:
                clip = clip.crop(x_center=clip.w/2, width=tw)
            
            clips.append(clip.fadein(0.2).fadeout(0.2))
        
        if not clips: return None

        final_video = mp.concatenate_videoclips(clips, method="compose")
        
        if audio_path and os.path.exists(audio_path):
            bg_audio = mp.AudioFileClip(audio_path).subclip(0, final_video.duration).audio_fadeout(2)
            if final_video.audio:
                final_video.audio = mp.CompositeAudioClip([bg_audio.volumex(0.7), final_video.audio.volumex(0.3)])
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
# INTERFACCIA
# ─────────────────────────────────────────

with st.sidebar:
    st.header("📍 Config")
    cat = st.selectbox("Tipo", ["DJ Set", "Musica dal Vivo", "Wedding", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    clip_duration = st.slider("Durata (s)", 1.0, 5.0, 2.5)
    audio_upload = st.file_uploader("Audio Soundtrack", type=["mp3", "wav"])
    files = st.file_uploader("Video (Max 10)", type=["mp4", "mov"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. ANALIZZA VIDEO"):
        results = []
        with st.status("🛸 AI sta analizzando...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(scan_single_video, f, cat) for f in files[:MAX_CLIPS]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res:
                        st.write("❌ Errore su: " + res['name'])
                    else:
                        st.write("✅ Pronto: " + res['name'])
            status.update(label="Analisi completata!", state="complete")
        st.session_state['h_list'] = results

    if 'h_list' in st.session_state:
        valid_h = [h for h in st.session_state['h_list'] if 'error' not in h]
        
        if valid_h:
            with st.expander("✏️ Modifica Highlights", expanded=True):
                for i, h in enumerate(valid_h):
                    cols = st.columns([1, 2, 3])
                    h['include'] = cols[0].checkbox("Usa", value=True, key=f"ch_{i}")
                    h['start'] = cols[1].number_input("Inizio (s)", value=float(h['start']), key=f"st_{i}")
                    cols[2].write("Motivo: " + h.get('reason', 'N/D'))
            
            if st.button("🎬 2. GENERA VIDEO FINALE"):
                to_render = [h for h in valid_h if h['include']]
                if to_render:
                    a_path = None
                    if audio_upload:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                            af.write(audio_upload.getvalue())
                            a_path = af.name
                    
                    with st.spinner("Creazione video..."):
                        final_path = render_sizzle(to_render, plat, ctype, clip_duration, a_path)
                    
                    if final_path:
                        st.video(final_path)
                        with open(final_path, "rb") as f:
                            st.download_button("📥 Scarica", f, file_name="sizzle_puglia.mp4")
                        if a_path: cleanup_temp_files([a_path])

if st.sidebar.button("🧹 Reset"):
    if 'h_list' in st.session_state:
        cleanup_temp_files([h['path'] for h in st.session_state['h_list'] if 'path' in h])
        del st.session_state['h_list']
    st.rerun()
