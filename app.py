import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Viral Lab Pro", page_icon="🚀", layout="wide")

# CSS per rendere l'app più professionale
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #FF0050; color: white; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧪 Viral Lab AI: Social Media Optimizer")

# --- GESTIONE API KEY SICURA ---
# Cerca la chiave nei Secrets di Streamlit, altrimenti chiede l'inserimento manuale
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Inserisci Gemini API Key", type="password")

if not api_key:
    st.error("⚠️ Configura la API Key nei Secrets o inseriscila nella barra laterale.")
    st.stop()

genai.configure(api_key=api_key)

# --- INPUT UTENTE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.header("1. Setup Contenuto")
    video_file = st.file_uploader("Carica il tuo video (MP4/MOV)", type=["mp4", "mov"])
    theme = st.text_input("Tema del video / Goal", placeholder="es. Recensione tech veloce e dinamica")
    
    platform = st.selectbox("Piattaforma Destinazione", ["TikTok", "Instagram", "Facebook"])
    format_type = st.selectbox("Formato", ["Reel/Story (9:16)", "Post Quadrato (1:1)", "Post Verticale (4:5)"])

# --- LOGICA DI FORMATTAZIONE ---
res_map = {
    "Reel/Story (9:16)": (1080, 1920),
    "Post Quadrato (1:1)": (1080, 1080),
    "Post Verticale (4:5)": (1080, 1350)
}

def process_video_format(video_path, target_res):
    clip = mp.VideoFileClip(video_path)
    target_w, target_h = target_res
    
    # Ridimensionamento e Crop automatico al centro
    # Questo assicura che il video riempia lo schermo senza barre nere
    clip_resized = clip.resize(height=target_h)
    if clip_resized.w > target_w:
        clip_resized = clip_resized.crop(x_center=clip_resized.w/2, width=target_w)
    
    return clip_resized

# --- ANALISI E GENERAZIONE ---
if st.button("🔥 GENERA CONTENUTO VIRALE") and video_file:
    with st.spinner("L'AI sta analizzando il video e ottimizzando il montaggio..."):
        # Salva file temporaneo
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(video_file.read())
        video_path = tfile.name

        # 1. Analisi Gemini 1.5 Flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        video_ai = genai.upload_file(path=video_path)
        
        prompt = f"""
        Analizza questo video per {platform} in formato {format_type}. Tema: {theme}.
        Usa le tue skills di viral growth hacker per identificare:
        1. Il gancio (hook) iniziale più forte.
        2. I momenti con più ritmicità.
        Restituisci un JSON:
        {{
          "start": secondo d'inizio taglio,
          "end": secondo di fine (max 15 sec totali),
          "overlay_text": "titolo accattivante",
          "caption": "caption virale con hashtag strategici",
          "music_trends": ["link o nome canzone 1", "2", "3"]
        }}
        """
        
        response = model.generate_content([video_ai, prompt])
        
        try:
            # Pulizia e parsing JSON
            raw_text = re.search(r'\{.*\}', response.text, re.DOTALL).group()
            data = json.loads(raw_text)
            
            # 2. Montaggio Video
            final_clip = process_video_format(video_path, res_map[format_type])
            final_clip = final_clip.subclip(float(data['start']), float(data['end']))
            
            output_file = "viral_ready.mp4"
            final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", fps=30)

            # --- DISPLAY RISULTATI ---
            with col2:
                st.header("2. Risultato Ottimizzato")
                st.video(output_file)
                
                st.subheader("💡 Strategia Virale")
                st.success(f"**Testo Hook consigliato:** {data['overlay_text']}")
                
                st.subheader("📝 Caption & Hashtags")
                st.code(data['caption'])
                
                st.subheader("🎵 Musiche in Trend (Cerca su App)")
                for song in data['music_trends']:
                    st.markdown(f"- {song}")
                
                with open(output_file, "rb") as f:
                    st.download_button("📥 SCARICA VIDEO PRONTO", f, file_name=f"{platform}_viral.mp4")

        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")