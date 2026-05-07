import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
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

# --- CONFIGURAZIONE STREAMLIT ---
st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0f1116; color: white; }
    .stButton>button {
        background: linear-gradient(90deg, #00f2ea, #FF0050);
        color: white; border: none; border-radius: 10px; height: 55px; width: 100%; font-weight: bold;
    }
    .stExpander { background-color: #1e2129; border-radius: 10px; }
    .platform-warning { background-color: #2a1f0f; border-left: 4px solid #FF0050; padding: 10px; border-radius: 5px; }
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
# Usiamo 1.5 Flash perché è il più veloce e supporta l'analisi video
MODEL_ID = "gemini-1.5-flash" 

PLATFORM_LIMITS = {
    "Instagram": {"Reels": 90,  "Storie": 60,  "Post": 60},
    "TikTok":    {"Reels": 180, "Storie": 60,  "Post": 180},
    "Facebook":  {"Reels": 60,  "Storie": 20,  "Post": 240},
}

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)}
}

DEFAULT_PROMPT = (
    "Sei un video editor professionista di Bari specializzato in contenuti virali Puglia. "
    "Analizza questo video di {cat} e trova il momento di picco energetico "
    "(drop, acuto, brindisi, emozione forte). "
    "Rispondi SOLO con JSON valido: "
    '{"start": float, "reason": "breve spiegazione", "music": "3 canzoni trend Italia"}'
)

# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def cleanup_temp_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except: pass

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

        window_start = max(0, start_hint - 10)
        window_end = min(duration, start_hint + 10)
        idx_start = int(window_start / step)
        idx_end = int(window_end / step)

        window_rms = rms_values[idx_start:idx_end]
        if window_rms:
            peak_idx = idx_start + int(np.argmax(window_rms))
            return float(timestamps[peak_idx])
        return start_hint
    except: return start_hint

def scan_single_video(f, prompt_template, cat):
    p = ""
    v_ai = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(3)
        
        model = genai.GenerativeModel(MODEL_ID)
        prompt = prompt_template.replace("{cat}", cat)
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

def render_sizzle(data_to_use, plat, ctype, clip_duration, add_watermark, watermark_text, audio_path):
    tw, th = FMT[plat][ctype]
    clips = []
    progress_bar = st.progress(0)

    for i, d in enumerate(data_to_use):
        try:
            v = mp.VideoFileClip(d['path'])
            start_time = float(d.get('start', 0))
            dur = float(d.get('clip_duration_override', clip_duration))
            end_time = min(start_time + dur, v.duration)

            clip = v.subclip(start_time, end_time).resize(height=th)
            final_clip = clip.crop(x_center=clip.w / 2, width=tw) if clip.w > tw else clip
            final_clip = final_clip.fadein(0.1).fadeout(0.1)

            if add_watermark and watermark_text.strip():
                try:
                    txt = mp.TextClip(watermark_text, fontsize=30, color='white', font='Arial-Bold', method='caption')
                    txt = txt.set_duration(final_clip.duration).set_position(('center', 'bottom')).margin(bottom=20, opacity=0)
                    final_clip = mp.CompositeVideoClip([final_clip, txt])
                except: pass

            clips.append(final_clip)
            # Non chiudiamo v qui perché serve per il concatenamento
        except Exception as err:
            st.warning(f"Errore clip {d['name']}: {err}")
        progress_bar.progress((i + 1) / len(data_to_use))

    if not clips: return None

    sizzle = mp.concatenate_videoclips(clips, method="compose")
    
    if audio_path and os.path.exists(audio_path):
        try:
            bg_audio = mp.AudioFileClip(audio_path).subclip(0, sizzle.duration).audio_fadeout(2)
            if sizzle.audio:
                sizzle = sizzle.set_audio(mp.CompositeAudioClip([bg_audio.volumex(0.8), sizzle.audio.volumex(0.3)]))
            else:
                sizzle = sizzle.set_audio(bg_audio)
        except: pass

    out = f"sizzle_{int(time.time())}.mp4"
    sizzle.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, preset='ultrafast', logger=None)
    
    # Pulizia clip
    for c in clips: c.close()
    sizzle.close()
    return out

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.header("📍 Configurazione")
    cat = st.selectbox("Tipo Contenuto", ["DJ Set", "Musica dal Vivo", "Wedding Puglia", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    
    clip_duration = st.slider("Durata clip (s)", 1.0, 5.0, 2.5)
    
    st.divider()
    add_watermark = st.toggle("Watermark")
    watermark_text = st.text_input("Testo", "#PugliaSizzle") if add_watermark else ""
    
    audio_upload = st.file_uploader("Audio Background", type=["mp3", "wav"])
    
    custom_prompt = st.text_area("AI Prompt", value=DEFAULT_PROMPT)
    
    files = st.file_uploader("Video (Max 10)", type=["mp4", "mov"], accept_multiple_files=True)

# ─────────────────────────────────────────
# LOGICA
# ─────────────────────────────────────────
if files:
    if st.button("🔎 1. ANALIZZA VIDEO (GEMINI 1.5)"):
        results = []
        with st.status("Analizzando i video...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(scan_single_video, f, custom_prompt, cat) for f in files[:MAX_CLIPS]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res: st.error(f"Errore {res['name']}: {res['error']}")
                    else: st.write(f"✅ {res['name']} pronto.")
        st.session_state['h_list'] = results

    if 'h_list' in st.session_state:
        h_list = st.session_state['h_list']
        valid_h = [h for h in h_list if 'error' not in h]
        
        with st.expander("✏️ Modifica Highlights", expanded=True):
            for i, h in enumerate(valid_h):
                cols = st.columns([1, 2, 2])
                h['include'] = cols[0].checkbox("OK", value=True, key=f"ch_{i}")
                h['start'] = cols[1].number_input("Inizio", value=float(h['start']), key=f"st_{i}")
                cols[2].caption(f"🤖 {h.get('reason', '')}")

        if st.button("🎬 2. GENERA VIDEO FINALE"):
            to_render = [h for h in valid_h if h['include']]
            
            # Gestione audio
            a_path = None
            if audio_upload:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                    af.write(audio_upload.getvalue())
                    a_path = af.name
            
            with st.spinner("Rendering in corso..."):
                final_path = render_sizzle(to_render, plat, ctype, clip_duration, add_watermark, watermark_text, a_path)
            
            if final_path:
                st.video(final_path)
                with open(final_path, "rb") as f:
                    st.download_button("📥 Scarica Video", f, file_name="puglia_sizzle.mp4")
                if a_path: cleanup_temp_files([a_path])

# Pulizia finale
if st.sidebar.button("🧹 Reset Sessione"):
    if 'h_list' in st.session_state:
        cleanup_temp_files([h['path'] for h in st.session_state['h_list'] if 'path' in h])
        del st.session_state['h_list']
    st.rerun()
