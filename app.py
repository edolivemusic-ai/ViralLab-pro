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

# Patch per ImageMagick su Streamlit Cloud
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# Formati per le piattaforme (Reels, Storie, Post)
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

def get_audio_peak(video_path, start_hint=0.0):
    try:
        v = mp.VideoFileClip(video_path)
        if v.audio is None: return start_hint
        step = 0.5
        timestamps = np.arange(0, max(0, v.duration - step), step)
        rms_values = [np.sqrt(np.mean(v.audio.subclip(t, min(t + step, v.duration)).to_soundarray(fps=22050)**2)) for t in timestamps]
        v.close()
        idx = int(max(0, start_hint - 5) / step)
        idx_end = int(min(len(rms_values), (start_hint + 5) / step))
        return float(timestamps[idx + np.argmax(rms_values[idx:idx_end])])
    except: return start_hint

def scan_single_video(f, cat):
    """Funzione di analisi con auto-riparazione del modello."""
    p = ""
    v_ai = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(2)
        
        # PROVA 1: Nomi diversi del modello per evitare il 404
        model_names_to_try = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "models/gemini-1.5-flash"]
        response = None
        last_err = ""

        for m_name in model_names_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                prompt = f"Analizza questo video di {cat}. Trova il picco energetico. Rispondi SOLO JSON: {{\"start\": float, \"reason\": string}}"
                response = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                if response: break 
            except Exception as e:
                last_err = str(e)
                continue
        
        if not response:
            raise Exception(f"Tutti i modelli hanno fallito. Ultimo errore: {last_err}")

        d = json.loads(response.text)
        start_time = get_audio_peak(p, float(d.get('start', 0)))
        
        return {'start': start_time, 'path': p, 'name': f.name, 'include': True, 'reason': d.get('reason','')}
    
    except Exception as err:
        if p and os.path.exists(p): os.unlink(p)
        return {'error': str(err), 'name': f.name}
    finally:
        if v_ai:
            try: genai.delete_file(v_ai.name)
            except: pass

def render_sizzle(data, plat, ctype, dur, audio_p):
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data:
            v = mp.VideoFileClip(d['path'])
            c = v.subclip(d['start'], min(d['start'] + dur, v.duration)).resize(height=th)
            if c.w > tw: c = c.crop(x_center=c.w/2, width=tw)
            clips.append(c.fadein(0.2).fadeout(0.2))
        
        final = mp.concatenate_videoclips(clips, method="compose")
        if audio_p:
            bg = mp.AudioFileClip(audio_p).subclip(0, final.duration).audio_fadeout(2)
            if final.audio: final.audio = mp.CompositeAudioClip([bg.volumex(0.7), final.audio.volumex(0.3)])
            else: final.audio = bg
        
        out = f"out_{int(time.time())}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        return out
    except Exception as e:
        st.error(f"Errore render: {e}"); return None

# --- UI ---
st.title("🎬 Puglia Sizzle Lab ☀️")

with st.sidebar:
    st.header("📍 Opzioni")
    cat = st.selectbox("Evento", ["DJ Set", "Musica", "Wedding"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    dur = st.slider("Durata clip (s)", 1.0, 5.0, 2.5)
    audio_up = st.file_uploader("Audio (MP3)", type=["mp3"])
    files = st.file_uploader("Video (Max 10)", type=["mp4"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. ANALIZZA"):
        results = []
        with st.status("Analisi AI...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(scan_single_video, f, cat) for f in files[:10]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res: st.error(f"❌ {res['name']}: {res['error']}")
                    else: st.write(f"✅ {res['name']} OK")
        st.session_state['h_list'] = results

    if 'h_list' in st.session_state:
        valid = [h for h in st.session_state['h_list'] if 'error' not in h]
        if valid:
            with st.expander("✏️ Modifica"):
                for i, h in enumerate(valid):
                    h['include'] = st.checkbox(f"Usa {h['name']}", value=True, key=f"c{i}")
                    h['start'] = st.number_input(f"Inizio {h['name']}", value=float(h['start']), key=f"s{i}")
            
            if st.button("🎬 2. GENERA"):
                ap = None
                if audio_up:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                        af.write(audio_up.getvalue()); ap = af.name
