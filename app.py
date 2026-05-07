import streamlit as st
import PIL.Image

# --- 1. FIX COMPATIBILITÀ PILLOW ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = 1 

import google.generativeai as genai
import moviepy.editor as mp
from moviepy.config import change_settings
import tempfile
import os
import json
import time
import concurrent.futures
import numpy as np

# Configurazione FFmpeg
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

genai.configure(api_key=api_key, transport='rest')
MODEL_ID = "gemini-1.5-flash"

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# ─────────────────────────────────────────
# FUNZIONI CORE
# ─────────────────────────────────────────

def get_audio_peak(p, hint):
    try:
        v = mp.VideoFileClip(p)
        if not v.audio: return hint
        step = 0.5
        ts = np.arange(0, max(0, v.duration - step), step)
        rms = []
        for t in ts:
            chunk = v.audio.subclip(t, min(t + step, v.duration)).to_soundarray(fps=22050)
            rms.append(np.sqrt(np.mean(chunk**2)))
        v.close()
        idx_s = int(max(0, hint - 3) / step)
        idx_e = int(min(len(rms), (hint + 3) / step))
        return float(ts[idx_s + np.argmax(rms[idx_s:idx_e])])
    except: return hint

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
        prompt = f"Analizza questo video di {cat}. Trova i 4 momenti migliori. Rispondi SOLO con una lista JSON di 4 oggetti: [{{'start': float, 'reason': string}}]"
        
        r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
        highlights = json.loads(r.text)
        
        results = []
        for i, h in enumerate(highlights):
            start_t = get_audio_peak(p, float(h.get('start', 0)))
            results.append({
                'start': start_t,
                'path': p,
                'name': f"{f.name} (Clip {i+1})",
                'include': True,
                'reason': h.get('reason', '')
            })
        return results
    except Exception as err:
        if p and os.path.exists(p): os.unlink(p)
        return [{'error': str(err), 'name': f.name}]
    finally:
        if v_ai:
            try: genai.delete_file(v_ai.name)
            except: pass

def render_sizzle(data, plat, ctype, dur, audio_p):
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data:
            if not d.get('include') or 'error' in d: continue
            v = mp.VideoFileClip(d['path'])
            c = v.subclip(d['start'], min(d['start'] + dur, v.duration)).resize(height=th)
            if c.w > tw: c = c.crop(x_center=c.w/2, width=tw)
            clips.append(c.fadein(0.1).fadeout(0.1))
        
        if not clips: return None
        final = mp.concatenate_videoclips(clips, method="compose")
        
        if audio_p:
            bg = mp.AudioFileClip(audio_p).subclip(0, final.duration).audio_fadeout(2)
            if final.audio:
                final.audio = mp.CompositeAudioClip([bg.volumex(0.8), final.audio.volumex(0.2)])
            else:
                final.audio = bg
        
        out = f"final_{int(time.time())}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        return out
    except Exception as e:
        st.error(f"Errore render: {e}")
        return None

# ─────────────────────────────────────────
# INTERFACCIA
# ─────────────────────────────────────────

st.title("🎬 Puglia Sizzle Lab Pro ☀️")

with st.sidebar:
    st.header("📍 Configurazione")
    cat = st.selectbox("Evento", ["DJ Set", "Wedding Puglia", "Musica"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    dur = st.slider("Durata clip (s)", 1.0, 4.0, 2.5)
    audio_up = st.file_uploader("Audio Soundtrack (MP3)", type=["mp3"])
    files = st.file_uploader("Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. ANALIZZA HIGHLIGHTS AI", type="primary"):
        all_res = []
        with st.status("Analisi in corso...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(scan_single_video, f, cat) for f in files[:10]]
                for future in concurrent.futures.as_completed(futures):
                    res_list = future.result()
                    for r in res_list:
                        all_res.append(r)
                        if 'error' not in r: st.write(f"✅ Trovato momento in {r['name']}")
        st.session_state['h_list'] = all_res

    if 'h_list' in st.session_state:
        valid = [h for h in st.session_state['h_list'] if 'error' not in h]
        if valid:
            with st.expander("✏️ Gestisci i tagli", expanded=True):
                for i, h in enumerate(valid):
                    c1, c2 = st.columns([1, 4])
                    h['include'] = c1.checkbox("Usa", value=True, key=f"k_{i}")
                    c2.info(f"{h['name']}: {h['reason']}")

            if st.button("🎬 2. GENERA VIDEO FINALE", type="primary"):
                ap = None
                if audio_up:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                        af.write(audio_up.getvalue())
                        ap = af.name
                
                with st.spinner("Creazione video..."):
                    fp = render_sizzle(valid, plat, ctype, dur, ap)
                
                if fp:
                    st.video(fp)
                    st.download_button("📥 Scarica", open(fp, "rb"), file_name="puglia_sizzle.mp4")

if st.sidebar.button("🧹 Reset"):
    st.session_state.clear()
    st.rerun()
