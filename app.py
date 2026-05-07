import streamlit as st
import PIL.Image

# --- SUPER-PATCH PILLOW ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.Resampling = PIL.Image

import google.generativeai as genai
import moviepy.editor as mp
from moviepy.config import change_settings
import tempfile
import os
import json
import time
import concurrent.futures
import numpy as np

if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide", page_icon="🎬")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

genai.configure(api_key=api_key, transport='rest')

@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower()]
        return models[0] if models else "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

WORKING_MODEL = get_working_model()

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
        rms = [np.sqrt(np.mean(v.audio.subclip(t, min(t + step, v.duration)).to_soundarray(fps=22050)**2)) for t in ts]
        v.close()
        idx_s = int(max(0, hint - 3) / step)
        idx_e = int(min(len(rms), (hint + 3) / step))
        return float(ts[idx_s + np.argmax(rms[idx_s:idx_e])])
    except: return hint

def scan_single_video(f, cat, m_name):
    p = ""
    v_ai = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(2)
        
        model = genai.GenerativeModel(m_name)
        # Chiediamo 3 highlights per video per avere più materiale
        prompt = f"""Analizza questo video di {cat}. 
        Trova i 3 momenti migliori e più energetici (es. drop, folla che balla, dettaglio tecnico).
        Rispondi SOLO con una lista JSON di oggetti: 
        [
          {{"start": float, "reason": "descrizione 1"}},
          {{"start": float, "reason": "descrizione 2"}},
          {{"start": float, "reason": "descrizione 3"}}
        ]"""
        
        r = model.generate_content([v_ai, prompt], generation_config={"response
