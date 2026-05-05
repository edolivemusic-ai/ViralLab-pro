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
    st.error("⚠️ Configura GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- CONFIGURAZIONE FORMATI ---
FORMAT_MAP = {
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)},
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- FUNZIONE DI MONTAGGIO ---
def auto_edit_video(input_path, platform, content_type, start_sec, end_sec):
    video = mp.VideoFileClip(input_path)
    target_w, target_h = FORMAT_MAP[platform][content_type]
    
    # Taglio
    video_cut = video.subclip(max(0, float(start_sec)), min(float(end_sec), video.duration))
    
    # Resize e Crop
    video_rescaled = video_cut.resize(height=target_h)
    if video_rescaled.w > target_w:
        video_final = video_rescaled.crop(x_center=video_rescaled.w/2, width=target_w)
    else:
        video_final = video_rescaled
        
    out_path = f"viral_export_{int(time.time())}.mp4"
    video_final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast')
    video.close()
    return out_path

# --- INTERFACCIA ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

# --- LOGICA DI ELABORAZIONE ---
if files and st.button("✨ GENERA VIDEO AUTOMATICI"):
    for f in files:
        with st.status(f"Lavorando su: {f.name}") as status:
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name

            try:
                # 1. Caricamento su Google
                status.update(label="Caricamento su Google AI...")
                video_ai = genai.upload_file(path=p)
                
                # 2. Attesa attiva (Polling)
                while True:
                    file_info = genai.get_file(video_ai.name)
                    if file_info.state.name == "ACTIVE":
                        break
                    if file_info.state.name == "FAILED":
                        raise Exception("L'elaborazione del video su Google è fallita.")
                    status.update(label=f"Google sta analizzando il video ({file_info.state.name})...")
                    time.sleep(4)
                
                # 3. ANALISI CON RETRY (Risolve l'errore NotFound)
                status.update(label="L'AI sta montando il video (momento clou)...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Sei un esperto di {cat}. Analizza il video per {plat} {ctype}. Trova il momento migliore tra 7 e 12 secondi. Restituisci SOLO JSON: {{'start': secondi, 'end': secondi, 'hook': 'testo', 'caption': 'testo'}}"
                
                response = None
                for attempt in range(3): # Riprova 3 volte se dà NotFound
                    try:
                        time.sleep(3) # Pausa di sicurezza
                        response = model.generate_content([video_ai, prompt])
                        if response: break
                    except exceptions.NotFound:
                        if attempt < 2:
                            status.update(label=f"Sincronizzazione API in corso (Tentativo {attempt+1})...")
                            time.sleep(5)
                        else: raise

                # 4. Parsing e Montaggio
                res = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                status.update(label="Taglio e Formattazione video in corso...")
                output = auto_edit_video(p, plat, ctype, res['start'], res['end'])
                
                # 5. Risultato
                st.video(output)
                st.success(f"Video {f.name} completato!")
                st.code(res['caption'])
                with open(output, "rb") as file_ready:
                    st.download_button(f"📥 Scarica {f.name}", file_ready, file_name=f"viral_{f.name}")
                
            except Exception as e:
                st.error(f"Errore su {f.name}: {e}")
            finally:
                if os.path.exists(p): os.remove(p)
                try: genai.delete_file(video_ai.name)
                except: pass
