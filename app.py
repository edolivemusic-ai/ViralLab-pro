import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re
import time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Music Viral Lab Pro", page_icon="🎙️", layout="wide")

# Design del pulsante e dell'interfaccia
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 12px; font-size: 20px; border-radius: 10px; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab: Montaggio Automatico")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Inserisci la API Key nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- CONFIGURAZIONE FORMATI ---
# Qui definiamo le dimensioni esatte per ogni social
FORMAT_MAP = {
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)},
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- FUNZIONE DI MONTAGGIO AUTOMATICO ---
def auto_edit_video(input_path, platform, content_type, start_sec, end_sec):
    # Carica il video
    video = mp.VideoFileClip(input_path)
    
    # 1. TAGLIO AUTOMATICO (Durata ideale)
    video_cut = video.subclip(float(start_sec), float(end_sec))
    
    # 2. RIDIMENSIONAMENTO AUTOMATICO (Crop e Resize)
    target_w, target_h = FORMAT_MAP[platform][content_type]
    
    # Ridimensiona in base all'altezza desiderata
    video_rescaled = video_cut.resize(height=target_h)
    
    # Crop centrale se il video è troppo largo (es. video orizzontale -> verticale)
    if video_rescaled.w > target_w:
        video_final = video_rescaled.crop(x_center=video_rescaled.w/2, width=target_w)
    else:
        video_final = video_rescaled # Già perfetto o più stretto
        
    out_path = f"export_{int(time.time())}.mp4"
    # Scrittura del file (ottimizzata per velocità)
    video_final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast')
    
    video.close() # Chiude il file per liberare memoria
    return out_path

# --- INTERFACCIA UTENTE ---
with st.sidebar:
    st.header("1. Impostazioni")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("2. Carica i tuoi video", type=["mp4", "mov"], accept_multiple_files=True)

# --- PROCESSO ---
if files and st.button("✨ AVVIA MONTAGGIO AUTOMATICO"):
    for f in files:
        with st.status(f"Processando {f.name}...") as status:
            # Salva temporaneo
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name

            # Analisi AI
            video_ai = genai.upload_file(path=p)
            while video_ai.state.name == "PROCESSING":
                time.sleep(3)
                video_ai = genai.get_file(video_ai.name)
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Sei un esperto di {cat}. Analizza il video per {plat} {ctype}. Trova il momento migliore tra 7 e 12 secondi. Restituisci SOLO JSON: {{'start': secondi, 'end': secondi, 'hook': 'testo', 'caption': 'testo'}}"
            
            response = model.generate_content([video_ai, prompt])
            try:
                # Estrae i dati del taglio
                res = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                
                # Esegue il montaggio fisico
                status.update(label="AI ha deciso i tempi. Montaggio in corso...")
                output = auto_edit_video(p, plat, ctype, res['start'], res['end'])
                
                # Mostra il risultato
                st.video(output)
                st.success(f"Video tagliato e formattato per {plat}!")
                st.code(res['caption'])
                with open(output, "rb") as file_ready:
                    st.download_button(f"📥 Scarica {f.name}", file_ready, file_name=f"viral_{f.name}")
                
            except Exception as e:
                st.error(f"Errore: {e}")
            finally:
                if os.path.exists(p): os.remove(p)
                genai.delete_file(video_ai.name)
