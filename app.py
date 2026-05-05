import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re
import time

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
    st.warning("⚠️ Inserisci la tua API Key nei Secrets di Streamlit per sbloccare l'AI.")
    st.stop()

genai.configure(api_key=api_key)

# --- MAPPA FORMATI E RISOLUZIONI ---
FORMAT_CONFIG = {
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)}, 
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- LOGICA VIDEO ---
def process_video_advanced(input_path, platform, content_type):
    clip = mp.VideoFileClip(input_path)
    target_w, target_h = FORMAT_CONFIG[platform][content_type]
    
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
    category = st.selectbox("Cosa hai filmato?", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    platform = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    content_type = st.radio("Tipo di Contenuto", ["Reels", "Storie", "Post"])
    st.divider()
    uploaded_files = st.file_uploader("📤 trascina qui i video", type=["mp4", "mov"], accept_multiple_files=True)

# --- PROCESSO BATCH ---
if uploaded_files and st.button("✨ GENERA CONTENUTI VIRALI"):
    
    for uploaded_file in uploaded_files:
        with st.status(f"Elaborando {uploaded_file.name}...") as status:
            
            # 1. Salva temporaneamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                tfile.write(uploaded_file.read())
                path = tfile.name

            # 2. Caricamento su Google AI
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                video_ai = genai.upload_file(path=path)
                
                # 3. ATTESA ROBUSTA ELABORAZIONE
                while True:
                    file_info = genai.get_file(video_ai.name)
                    if file_info.state.name == "ACTIVE":
                        break
                    elif file_info.state.name == "FAILED":
                        st.error(f"Errore Google nell'elaborazione del video {uploaded_file.name}")
                        st.stop()
                    status.update(label=f"Analisi video in corso ({file_info.state.name})...")
                    time.sleep(3)
                
                # Attesa extra per sincronizzazione API
                time.sleep(2)

                # 4. Prompt Strategico
                prompt = f"""
                Sei un esperto Social Media Manager per {category}.
                Ottimizza questo video per {platform} ({content_type}).
                Restituisci SOLO un JSON:
                {{
                  "start": secondo d'inizio (numero),
                  "end": secondo di fine (numero),
                  "hook_text": "titolo gancio",
                  "caption": "caption virale",
                  "hashtags": "hashtag strategici",
                  "viral_reason": "perché funzionerà"
                }}
                """
                
                # Tentativo di generazione con retry
                response = model.generate_content([video_ai, prompt])
                data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                
                # 5. Montaggio Video Fisico
                status.update(label=f"Montaggio {platform}...", state="running")
                edited_clip = process_video_advanced(path, platform, content_type)
                
                v_start = float(data['start'])
                v_end = min(float(data['end']), edited_clip.duration)
                
                final_video = edited_clip.subclip(v_start, v_end)
                out_path = f"viral_{uploaded_file.name}"
                final_video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=30, logger=None)
                
                # Visualizzazione
                with col_main:
                    with st.expander(f"🎬 {uploaded_file.name} PRONTO", expanded=True):
                        v_col, t_col = st.columns([1, 1.2])
                        with v_col:
                            st.video(out_path)
                            with open(out_path, "rb") as f:
                                st.download_button(f"📥 SCARICA", f, file_name=f"{platform}_{uploaded_file.name}")
                        with t_col:
                            st.success(f"**Strategia:** {data['viral_reason']}")
                            st.markdown(f"**🪝 Hook:** `{data['hook_text']}`")
                            st.code(f"{data['caption']}\n\n{data['hashtags']}", language="text")
                
            except Exception as e:
                st.error(f"Errore su {uploaded_file.name}: {str(e)}")
            finally:
                if os.path.exists(path): os.remove(path)
                # Pulisce il file dai server Google per non occupare spazio
                try: genai.delete_file(video_ai.name)
                except: pass
