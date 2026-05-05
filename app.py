import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re
import time
from google.api_core import exceptions

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Music Viral Lab Pro", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 12px; font-size: 20px; border-radius: 10px; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab: All-in-One")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Configura GEMINI_API_KEY nei Secrets.")
    st.stop()

genai.configure(api_key=api_key)

FORMAT_MAP = {
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)},
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- FUNZIONE DI MONTAGGIO (OTTIMIZZATA RAM) ---
def auto_edit_video(input_path, platform, content_type, start_sec, end_sec):
    with mp.VideoFileClip(input_path) as video:
        target_w, target_h = FORMAT_MAP[platform][content_type]
        
        # Taglio immediato per risparmiare memoria
        start = max(0, float(start_sec))
        end = min(float(end_sec), video.duration)
        if end <= start: end = start + 10
        
        clip = video.subclip(start, end)
        
        # Resize e Crop
        clip_res = clip.resize(height=target_h)
        if clip_res.w > target_w:
            final = clip_res.crop(x_center=clip_res.w/2, width=target_w)
        else:
            final = clip_res
            
        out_path = f"final_{int(time.time())}.mp4"
        # Parametri critici per non far crashare il server
        final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, 
                              logger=None, preset='ultrafast', threads=1)
        return out_path

# --- INTERFACCIA ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

# Contenitore per i risultati (fuori dai loop di stato)
result_container = st.container()

# --- LOGICA ---
if files and st.button("✨ GENERA VIDEO AUTOMATICI"):
    for f in files:
        # 1. Salvataggio locale
        t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        t.write(f.read())
        p = t.name
        
        video_ai = None
        
        try:
            with st.status(f"🛠️ Elaborazione: {f.name}") as status:
                # 2. Caricamento Google
                status.update(label="Caricamento su Google AI...")
                video_ai = genai.upload_file(path=p)
                
                # 3. Attesa (molto più lunga per sicurezza)
                while True:
                    file_info = genai.get_file(video_ai.name)
                    if file_info.state.name == "ACTIVE":
                        break
                    status.update(label=f"Google sta indicizzando il video ({file_info.state.name})...")
                    time.sleep(5)
                
                # Pausa extra: il NotFound capita se chiediamo subito dopo "ACTIVE"
                time.sleep(10) 
                
                # 4. Analisi AI con retry
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Sei un esperto di {cat}. Analizza il video per {plat} {ctype}. Trova il momento clou (7-12 sec). Rispondi SOLO JSON: {{'start': sec, 'end': sec, 'hook': 'testo', 'caption': 'testo'}}"
                
                response_text = ""
                for attempt in range(4):
                    try:
                        resp = model.generate_content([video_ai, prompt])
                        response_text = resp.text
                        break
                    except exceptions.NotFound:
                        status.update(label=f"Sincronizzazione in corso (Tentativo {attempt+1})...")
                        time.sleep(8)
                
                # 5. Montaggio
                status.update(label="AI ha deciso i tempi. Montagg
