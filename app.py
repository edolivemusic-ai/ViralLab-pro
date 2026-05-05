import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image
from google.api_core import exceptions

# --- PATCH COMPATIBILITÀ ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Puglia Sizzle Lab ☀️", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:#f0f2f6;}.stButton>button{background:linear-gradient(90deg,#FF0050 0%,#00f2ea 100%);color:white;border-radius:10px;width:100%;}</style>", unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Il Super-Montaggio 🌊")
st.subheader("Bari & Puglia Event Edition - Dai video grezzi al Reel finale")

# --- API ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Inserisci la API KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280)}
}

# --- LOGICA DI MONTAGGIO RITMICO ---
def create_sizzle_reel(clips_data, platform, content_type):
    target_w, target_h = FMT[platform][content_type]
    processed_clips = []
    
    for item in clips_data:
        try:
            video = mp.VideoFileClip(item['path'])
            # Taglio del momento highlight
            sub = video.subclip(float(item['start']), float(item['end']))
            # Adattamento formato e resize
            sub_res = sub.resize(height=target_h)
            if sub_res.w > target_w:
                sub_final = sub_res.crop(x_
