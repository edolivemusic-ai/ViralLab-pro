import streamlit as st
import PIL.Image

# --- 1. FIX COMPATIBILITÀ (Deve essere la prima cosa nel codice) ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    # Fix per Python 3.12/3.14 e Pillow 10+
    PIL.Image.ANTIALIAS = 1 # Equivalente a Resampling.LANCZOS

import google.generativeai as genai
import moviepy.editor as mp
from moviepy.config import change_settings
import tempfile
import os
import json
import time
import concurrent.futures
import numpy as np

# Configurazione FFmpeg e ImageMagick
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide", page_icon="🎬")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

# Forziamo REST per evitare blocchi di rete su Streamlit Cloud
genai.configure(api_key=api_key, transport='rest')

# Modello più stabile per video
MODEL_ID = "gemini-1.5-flash-002"

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# ─────────────────────────────────────────
# FUNZIONI CORE
# ─────────────────────────────────────────

def get_audio_peak(p, hint):
    """Analisi audio per centrare il taglio sul beat."""
    try:
        v = mp.VideoFileClip(p)
        if not v.audio: return hint
        step = 0.5
        ts = np.arange(0, max(0, v.duration - step), step)
        # Calcolo RMS manuale compatibile con Numpy < 2.0
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
    """Cerca 4 momenti migliori per ogni video per allungare il montaggio."""
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
        # Chiediamo 4 momenti invece di 1 per avere un video più lungo
        prompt = f"""Analizza questo video di {cat} (Puglia). 
        Trova i 4 momenti più energetici e spettacolari.
        Rispondi SOLO con una lista JSON di 4 oggetti: 
        [
          {{"start": 12.5, "reason": "descrizione"}},
          {{"start": 30.0, "reason": "descrizione"}},
          {{"start": 45.2, "reason": "descrizione"}},
          {{"start": 5.5, "reason": "descrizione"}}
        ]"""
        
        r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
        highlights = json.loads(r.text)
        
        results = []
        for i, h in enumerate(highlights):
            start_t = get_audio_peak(p, float(h.get('start', 0)))
            results.append({
                'start': start_t,
                'path': p,
                'name': f"{f.name} (Taglio {i+1})",
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
    """Esegue il montaggio finale."""
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data:
            if not d.get('include') or 'error' in d: continue
            v = mp.VideoFileClip(d['path'])
            # Taglio e resize protetto
            c = v.subclip(d['start'], min(d['start'] + dur, v.duration)).resize(height=th)
            if c.w > tw: c = c.crop(x_center=c.w/2, width=tw)
            clips.append(c.fadein(0.1).fadeout(0.1))
        
        if not clips: return None
        final = mp.concatenate_videoclips(clips, method="compose")
        
        if audio_p:
            bg = mp.AudioFileClip(audio_p).subclip(0, final.duration).audio_fadeout(2)
            if final.audio:
                final.audio = mp.CompositeAudioClip([bg.volumex(0.85), final.audio.volumex(0.15)])
            else:
                final.audio = bg
        
        out = f"puglia_sizzle_{int(time.time())}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        
        for c in clips: c.close()
        return out
    except Exception as e:
        st.error(f"Errore rendering: {e}")
        return None

# ─────────────────────────────────────────
# INTERFACCIA UTENTE
# ─────────────────────────────────────────

st.title("🎬 Puglia Sizzle Lab Pro ☀️")
st.markdown("---")

with st.sidebar:
    st.header("📍 Configurazione")
    cat = st.selectbox("Tipo Evento", ["DJ Set", "Live Music", "Wedding Puglia", "Karaoke"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    dur = st.slider("Ritmo tagli (durata clip in sec)", 1.0, 4
