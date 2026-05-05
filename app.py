import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Music Viral Lab 🎧", page_icon="🎸", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stSelectbox div[data-baseweb="select"] { background-color: #262730; }
    .stButton>button { background: linear-gradient(45deg, #FF0050, #00f2ea); color: white; font-weight: bold; height: 3em; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎧 Music Viral Lab: Event Edition")
st.subheader("Ottimizzato per DJ, Wedding Band e Live Music")

# --- SICUREZZA API ---
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Inserisci Gemini API Key", type="password")

if not api_key:
    st.error("⚠️ Configura la API Key per attivare l'AI.")
    st.stop()

genai.configure(api_key=api_key)

# --- FUNZIONI TECNICHE ---
def process_music_video(input_path, start, end, target_format):
    clip = mp.VideoFileClip(input_path)
    
    # Resize automatico per piattaforme social
    formats = {
        "Reel/TikTok (9:16)": (1080, 1920),
        "Post (1:1)": (1080, 1080),
        "Full HD (16:9)": (1920, 1080)
    }
    target_w, target_h = formats[target_format]
    
    # Ridimensionamento e Crop intelligente al centro
    clip = clip.resize(height=target_h)
    if clip.w > target_w:
        clip = clip.crop(x_center=clip.w/2, width=target_w)
    elif clip.h > target_h:
        clip = clip.crop(y_center=clip.h/2, height=target_h)
        
    final_clip = clip.subclip(float(start), float(end))
    out_name = f"viral_{tempfile.NamedTemporaryFile().name[-5:]}.mp4"
    final_clip.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=30, logger=None)
    return out_name

# --- INTERFACCIA DI INPUT ---
col_in, col_out = st.columns([1, 2])

with col_in:
    st.header("📂 Caricamento")
    # Menu a tendina richiesto
    category = st.selectbox("Categoria Contenuto", [
        "DJ Set", 
        "Musica dal Vivo", 
        "Karaoke", 
        "Wedding Music", 
        "Wedding Band"
    ])
    
    platform_format = st.selectbox("Ottimizza per:", ["Reel/TikTok (9:16)", "Post (1:1)", "Full HD (16:9)"])
    
    uploaded_files = st.file_uploader("Trascina i video della serata", type=["mp4", "mov"], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"🚀 RENDI VIRALI {len(uploaded_files)} VIDEO"):
        
        for file in uploaded_files:
            with st.status(f"Analisi {file.name}...") as status:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                    tfile.write(file.read())
                    path = tfile.name

                # PROMPT SPECIALIZZATO PER SETTORE MUSICALE / EVENTI
                model = genai.GenerativeModel('gemini-1.5-flash')
                video_ai = genai.upload_file(path=path)
                
                prompt = f"""
                Sei un Social Media Manager esperto nel settore {category}. 
                Analizza questo video e identifica il momento più virale basandoti sui competitor di successo (es. Boiler Room per DJ, video emozionali di matrimonio per Wedding Band).
                
                Obiettivo: Trovare il 'Hook' perfetto (un beat drop, un acuto, un momento di gioia degli ospiti, o un effetto luce).
                
                Restituisci un JSON puro:
                {{
                  "start": secondo d'inizio (identifica il picco di energia),
                  "end": secondo di fine (durata ideale 7-12 secondi),
                  "hook_strategy": "perché questo pezzo funzionerà",
                  "caption": "caption virale con emoji e ganci mentali",
                  "hashtags": "#weddingmusic #djset #trending",
                  "audio_advice": "consiglio su come mixare l'audio originale con un trend"
                }}
                """
                
                response = model.generate_content([video_ai, prompt])
                try:
                    data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                    
                    status.update(label="Montaggio e Formattazione...", state="running")
                    output_path = process_music_video(path, data['start'], data['end'], platform_format)
                    
                    with col_out:
                        with st.expander(f"⭐ RISULTATO: {category} - {file.name}", expanded=True):
                            v_col, t_col = st.columns(2)
                            with v_col:
                                st.video(output_path)
                            with t_col:
                                st.success(f"**Strategia:** {data['hook_strategy']}")
                                st.code(f"{data['caption']}\n\n{data['hashtags']}")
                                st.info(f"🎵 **Audio Tip:** {data['audio_advice']}")
                                with open(output_path, "rb") as f:
                                    st.download_button("📥 SCARICA", f, file_name=f"viral_{category}_{file.name}")
                    
                except Exception as e:
                    st.error(f"Errore su {file.name}: {e}")
                finally:
                    os.remove(path)
