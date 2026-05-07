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

# --- PATCH COMPATIBILITÀ ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Configurazione ImageMagick per Streamlit Cloud
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide", page_icon="🎬")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- SMART MODEL SELECTOR ---
def get_flash_model_name():
    """Trova il nome esatto del modello Flash disponibile per l'API Key."""
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if '1.5' in m.name and 'flash' in m.name:
                    return m.name
        return "models/gemini-1.5-flash" # Fallback
    except:
        return "gemini-1.5-flash"

# Determiniamo il modello una sola volta all'avvio
if 'model_name' not in st.session_state:
    st.session_state['model_name'] = get_flash_model_name()

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def cleanup_temp_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path): os.unlink(path)
        except: pass

def get_audio_peak(video_path, start_hint=0.0):
    try:
        v = mp.VideoFileClip(video_path)
        if v.audio is None:
            v.close(); return start_hint
        duration = v.duration
        step = 0.5
        timestamps = np.arange(0, max(0, duration - step), step)
        rms_values = []
        for t in timestamps:
            chunk = v.audio.subclip(t, min(t + step, duration))
            rms = np.sqrt(np.mean(chunk.to_soundarray(fps=22050)**2))
            rms_values.append(rms)
        v.close()
        window_start, window_end = max(0, start_hint - 5), min(duration, start_hint + 5)
        idx_start, idx_end = int(window_start / step), int(window_end / step)
        window_rms = rms_values[idx_start:idx_end]
        if window_rms:
            return float(timestamps[idx_start + int(np.argmax(window_rms))])
        return start_hint
    except: return start_hint

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
        
        # Usa il nome modello rilevato automaticamente
        model = genai.GenerativeModel(st.session_state['model_name'])
        
        prompt = f"Analizza questo video di {cat}. Trova il picco energetico e rispondi SOLO con JSON: {{\"start\": float, \"reason\": string}}"
        
        r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
        d = json.loads(r.text)
        
        ai_start = float(d.get('start', 0))
        audio_peak = get_audio_peak(p, start_hint=ai_start)
        
        d.update({'start_ai': ai_start, 'start': audio_peak, 'path': p, 'name': f.name, 'include': True})
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
            clip = v.subclip(start, min(start + float(clip_duration), v.duration)).resize(height=th)
            if clip.w > tw: clip = clip.crop(x_center=clip.w/2, width=tw)
            clips.append(clip.fadein(0.2).fadeout(0.2))
        
        if not clips: return None
        final_video = mp.concatenate_videoclips(clips, method="compose")
        
        if audio_path and os.path.exists(audio_path):
            bg = mp.AudioFileClip(audio_path).subclip(0, final_video.duration).audio_fadeout(2)
            if final_video.audio:
                final_video.audio = mp.CompositeAudioClip([bg.volumex(0.7), final_video.audio.volumex(0.3)])
            else:
                final_video.audio = bg
        
        out_name = f"sizzle_{int(time.time())}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        return out_name
    except Exception as e:
        st.error(f"Errore render: {e}"); return None

# ─────────────────────────────────────────
# INTERFACCIA STREAMLIT
# ─────────────────────────────────────────

st.title("🎬 Puglia Sizzle Lab ☀️")
st.caption(f"Modello AI rilevato: `{st.session_state['model_name']}`")

with st.sidebar:
    st.header("📍 Configurazione")
    cat = st.selectbox("Tipo Contenuto", ["DJ Set", "Musica dal Vivo", "Wedding Puglia", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    
    clip_duration = st.slider("Durata clip (s)", 1.0, 5.0, 2.5)
    st.divider()
    audio_upload = st.file_uploader("Audio Soundtrack (MP3)", type=["mp3", "wav"])
    st.divider()
    files = st.file_uploader("Carica Video (Max 10)", type=["mp4", "mov"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. ANALIZZA HIGHLIGHTS"):
        results = []
        with st.status("🛸 AI sta analizzando i video...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(scan_single_video, f, cat) for f in files[:10]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res:
                        st.error(f"❌ Errore su {res['name']}: {res['error']}")
                    else:
                        st.write(f"✅ Pronto: {res['name']}")
            status.update(label="Analisi completata!", state="complete")
        st.session_state['h_list'] = results

    if 'h_list' in st.session_state:
        valid_h = [h for h in st.session_state['h_list'] if 'error' not in h]
        
        if valid_h:
            with st.expander("✏️ Modifica Highlights", expanded=True):
                for i, h in enumerate(valid_h):
                    cols = st.columns([1, 2, 2])
                    h['include'] = cols[0].checkbox("Usa", value=True, key=f"ch_{i}")
                    h['start'] = cols[1].number_input("Inizio (s)", value=float(h['start']), key=f"st_{i}")
                    cols[2].caption(f"Motivo: {h.get('reason', 'N/D')}")

            if st.button("🎬 2. GENERA VIDEO FINALE"):
                to_render = [h for h in valid_h if h['include']]
                if to_render:
                    a_path = None
                    if audio_upload:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                            af.write(audio_upload.getvalue())
                            a_p = af.name
                    
                    with st.spinner("Creazione video..."):
                        final_path = render_sizzle(to_render, plat, ctype, clip_duration, a_path)
                    
                    if final_path:
                        st.success("Video generato!")
                        st.video(final_path)
                        with open(final_path, "rb") as f:
                            st.download_button("📥 Scarica", f, file_name="sizzle_puglia.mp4")
                        if a_path: cleanup_temp_files([a_path])

if st.sidebar.button("🧹 Reset"):
    if 'h_list' in st.session_state:
        cleanup_temp_files([h['path'] for h in st.session_state['h_list'] if 'path' in h])
        del st.session_state['h_list']
    st.rerun()
