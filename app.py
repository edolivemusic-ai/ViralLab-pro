import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re

# --- CONFIGURAZIONE E LAYOUT ---
st.set_page_config(page_title="Music Viral Lab Pro", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stSelectbox label, .stMultiSelect label { color: #00f2ea !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 15px; font-size: 20px; border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab: All-in-One Social Optimizer")

# --- SICUREZZA API ---
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Inserisci Gemini API Key", type="password")
if not api_key:
    st.warning("⚠️ Inserisci la tua API Key per sbloccare l'AI.")
    st.stop()

genai.configure(api_key=api_key)

# --- MAPPA FORMATI E RISOLUZIONI ---
# Formati: Reels/TikTok (9:16), Post (1:1 o 4:5), Storie (9:16)
FORMAT_CONFIG = {
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)}, # 4:5 per IG Post
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)} # 1:1 per FB Post
}

# --- LOGICA VIDEO ---
def process_video_advanced(input_path, platform, content_type):
    clip = mp.VideoFileClip(input_path)
    target_w, target_h = FORMAT_CONFIG[platform][content_type]
    
    # Ridimensionamento intelligente
    # Se il video è orizzontale, lo ingrandisce per riempire l'altezza e taglia i lati
    clip_resized = clip.resize(height=target_h)
    if clip_resized.w > target_w:
        clip_final = clip_resized.crop(x_center=clip_resized.w/2, width=target_w)
    else:
        clip_final = clip_resized.resize(width=target_w).crop(y_center=clip_resized.h/2, height=target_h)
        
    return clip_final

# --- INTERFACCIA ---
col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.header("⚙️ Preferenze")
    
    category = st.selectbox("Cosa hai filmato?", [
        "DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"
    ])
    
    platform = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    
    content_type = st.radio("Tipo di Contenuto", ["Reels", "Storie", "Post"])
    
    st.divider()
    
    uploaded_files = st.file_uploader("📤 trascina qui i video (anche multipli)", 
                                     type=["mp4", "mov"], 
                                     accept_multiple_files=True)

# --- PROCESSO BATCH ---
if uploaded_files and st.button("✨ GENERA CONTENUTI VIRALI"):
    
    for uploaded_file in uploaded_files:
        with st.status(f"Elaborando {uploaded_file.name}...") as status:
            
            # Salva temporaneamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                tfile.write(uploaded_file.read())
                path = tfile.name

            # AI AGENT SPECIALIZZATO
            model = genai.GenerativeModel('gemini-1.5-flash')
            video_ai = genai.upload_file(path=path)
            
            # Prompt Dinamico basato su Piattaforma e Formato
            prompt = f"""
            Sei un esperto Viral Strategist per {category}.
            Ottimizza questo contenuto per {platform} ({content_type}).
            
            Skills specifiche da applicare:
            - Se TikTok: focus su ritmi veloci, hook nei primi 2 secondi e 'chaos energy'.
            - Se Instagram Reels: focus su estetica, transizioni fluide e lifestyle aspirazionale.
            - Se Facebook: focus su interazione (domande nella caption) e condivisione familiare/emozionale.
            - Se Storie: stile più grezzo e 'dietro le quinte'.

            Restituisci JSON:
            {{
              "start": secondo d'inizio,
              "end": secondo di fine (max 12s),
              "hook_text": "titolo gancio",
              "caption": "caption ottimizzata per {platform}",
              "hashtags": "tag virali",
              "viral_reason": "perché questo taglio funzionerà su {platform}"
            }}
            """
            
            response = model.generate_content([video_ai, prompt])
            
            try:
                data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                
                # Editing Video Fisico
                status.update(label=f"Montaggio {platform} {content_type}...", state="running")
                edited_clip = process_video_advanced(path, platform, content_type)
                final_video = edited_clip.subclip(float(data['start']), float(data['end']))
                
                out_path = f"viral_{platform}_{uploaded_file.name}"
                final_video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=30, logger=None)
                
                # Visualizzazione nel Lab
                with col_main:
                    with st.expander(f"🎬 {uploaded_file.name} - PRONTO PER {platform.upper()}", expanded=True):
                        v_col, t_col = st.columns([1, 1.2])
                        with v_col:
                            st.video(out_path)
                            with open(out_path, "rb") as f:
                                st.download_button(f"📥 SCARICA PER {platform.upper()}", f, file_name=out_path)
                        with t_col:
                            st.markdown(f"**🎯 Strategia:** {data['viral_reason']}")
                            st.markdown(f"**🪝 Hook a video:** `{data['hook_text']}`")
                            st.code(f"{data['caption']}\n\n{data['hashtags']}", language="text")
                
            except Exception as e:
                st.error(f"Errore: {e}")
            finally:
                if os.path.exists(path): os.remove(path)
