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

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide", page_icon="🎬")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# --- COSTANTI ---
MODEL_ID = "gemini-1.5-flash" # Prova anche "gemini-1.5-flash-latest" se fallisce

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)}
}

def cleanup_temp_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path): os.unlink(path)
        except: pass

def get_audio_peak(video_path, start_hint=0.0):
    try:
        v = mp.VideoFileClip(video_path)
        if v.audio is None:
            v.close() ; return start_hint
        duration = v.duration
        step = 0.5
        timestamps = np.arange(0, max(0, duration - step), step)
        rms_values = [np.sqrt(np.mean(v.audio.subclip(t, min(t + step, duration)).to_soundarray(fps=22050)**2)) for t in timestamps]
        v.close()
        window_start, window_end = max(0, start_hint - 5), min(duration, start_hint + 5)
        idx_start, idx_end = int(window_start / step), int(window_end / step)
        window_rms = rms_values[idx_start:idx_end]
        if window_rms: return float(timestamps[idx_start + int(np.argmax(window_rms))])
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
        # Timeout di sicurezza: max 60 secondi di attesa processing
        wait_count = 0
        while genai.get_file(v_ai.name).state.name == "PROCESSING" and wait_count < 20:
            time.sleep(3)
            wait_count += 1
        
        model = genai.GenerativeModel(MODEL_ID)
        prompt = f"Analizza questo video di {cat}. Trova il picco energetico e rispondi SOLO con JSON: {{\"start\": float, \"reason\": string}}"
        
        r = model.generate_content(
            [v_ai, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
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
            clip = v.subclip(float(d['start']), min(float(d['start']) + float(clip_duration), v.duration)).resize(height=th)
            if clip.w > tw: clip = clip.crop(x_center=clip.w/2, width=tw)
            clips.append(clip.fadein(0.2).fadeout(0.2))
        
        if not clips: return None
        final_video = mp.concatenate_videoclips(clips, method="compose")
        if audio_path and os.path.exists(audio_path):
            bg = mp.AudioFileClip(audio_path).subclip(0, final_video.duration).audio_fadeout(2)
            if final_video.audio: final_video.audio = mp.CompositeAudioClip([bg.volumex(0.7), final_video.audio.volumex(0.3)])
            else: final_video.audio = bg
        
        out_name = f"sizzle_{int(time.time())}.mp4"
        final_video.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        return out_name
    except Exception as e:
        st.error(f"Errore render: {e}") ; return None

# --- UI ---
st.title("🎬 Puglia Sizzle Lab ☀️")
with st.sidebar:
    cat = st.selectbox("Tipo", ["DJ Set", "Musica", "Wedding"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok"])
    ctype = st.radio("Formato", ["Reels", "Post"])
    dur = st.slider("Durata (s)", 1.0, 5.0, 2.5)
    audio_up = st.file_uploader("Audio", type=["mp3"])
    files = st.file_uploader("Video", type=["mp4"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. ANALIZZA"):
        results = []
        with st.status("Analisi...") as status:
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
            with st.expander("Modifica Highlights"):
                for i, h in enumerate(valid):
                    h['include'] = st.checkbox(f"Usa {h['name']}", value=True, key=f"c{i}")
                    h['start'] = st.number_input(f"Inizio {h['name']}", value=float(h['start']), key=f"s{i}")
            
            if st.button("🎬 2. GENERA"):
                a_p = None
                if audio_up:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                        af.write(audio_up.getvalue())
                        a_p = af.name
                f_p = render_sizzle([h for h in valid if h['include']], plat, ctype, dur, a_p)
                if f_p:
                    st.video(f_p)
                    st.download_button("Scarica", open(f_p, "rb"), file_name="sizzle.mp4")
