import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import re

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Viral Lab Multi-Pro", page_icon="🧪", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stHeader { background-color: #FF0050; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Viral Lab: Batch Processor")
st.subheader("Carica più video, ottieni più contenuti virali in un colpo solo.")

# --- SICUREZZA API ---
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Inserisci Gemini API Key", type="password")

if not api_key:
    st.error("⚠️ Configura la API Key nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- FUNZIONE DI EDITING ---
def edit_video(input_path, start, end, target_format):
    clip = mp.VideoFileClip(input_path)
    
    # Formattazione Pro (Auto-Crop 9:16 per Reels/TikTok)
    if target_format == "9:16":
        target_w, target_h = (1080, 1920)
        clip = clip.resize(height=target_h)
        if clip.w > target_w:
            clip = clip.crop(x_center=clip.w/2, width=target_w)
    
    # Taglio
    final_clip = clip.subclip(float(start), float(end))
    out_name = f"viral_{tempfile.NamedTemporaryFile().name[-5:]}.mp4"
    final_clip.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, logger=None)
    return out_name

# --- AREA DI UPLOAD (MULTI) ---
col_in, col_out = st.columns([1, 2])

with col_in:
    st.header("📥 Input")
    theme = st.text_input("Tema comune o stile (es. Motivazionale, Vlog, Tutorial)")
    # ATTIVATO IL MULTI-UPLOAD
    uploaded_files = st.file_uploader("Trascina qui i tuoi video", type=["mp4", "mov"], accept_multiple_files=True)
    
    selected_format = st.selectbox("Formato finale", ["9:16", "1:1", "Originale"])

if uploaded_files and theme:
    if st.button(f"🔥 PROCESSA {len(uploaded_files)} VIDEO"):
        
        for i, file in enumerate(uploaded_files):
            st.write(f"--- ⏳ Elaborazione Video {i+1}: {file.name} ---")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
                tfile.write(file.read())
                path = tfile.name

            try:
                # 1. AI Analysis
                model = genai.GenerativeModel('gemini-1.5-flash')
                video_ai = genai.upload_file(path=path)
                
                prompt = f"Analizza questo video per tema: {theme}. Restituisci JSON puro: {{'start': sec, 'end': sec, 'hook': 'testo', 'caption': 'testo', 'tags': ['h1', 'h2']}}"
                
                response = model.generate_content([video_ai, prompt])
                res_clean = re.search(r'\{.*\}', response.text, re.DOTALL).group()
                data = json.loads(res_clean)

                # 2. MoviePy Editing
                output_video = edit_video(path, data['start'], data['end'], selected_format)

                # 3. Risultati
                with col_out:
                    with st.expander(f"✅ RISULTATO: {file.name}", expanded=True):
                        v_col, t_col = st.columns(2)
                        with v_col:
                            st.video(output_video)
                        with t_col:
                            st.info(f"🪝 Hook: {data['hook']}")
                            st.code(data['caption'])
                            st.write(f"Tags: {' '.join(data['tags'])}")
                            with open(output_video, "rb") as f:
                                st.download_button(f"Scarica {file.name}", f, file_name=f"viral_{file.name}")
                
                # Pulizia per non intasare il server
                os.remove(path)

            except Exception as e:
                st.error(f"Errore sul video {file.name}: {e}")
