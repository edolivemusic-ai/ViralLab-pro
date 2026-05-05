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

st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 10px; border-radius: 10px; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Inserisci Gemini API Key", type="password")
if not api_key:
    st.warning("⚠️ Inserisci la tua API Key nei Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# --- FORMATI ---
FORMAT_CONFIG = {
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)}, 
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- FUNZIONE VIDEO (OTTIMIZZATA PER RAM) ---
def process_video_optimized(input_path, platform, content_type, start, end):
    # Carichiamo la clip solo per il pezzetto che ci serve (risparmio RAM)
    with mp.VideoFileClip(input_path) as video:
        target_w, target_h = FORMAT_CONFIG[platform][content_type]
        
        # Taglio immediato (subclip) per non processare tutto il video
        v_start = float(start)
        v_end = min(float(end), video.duration)
        short_clip = video.subclip(v_start, v_end)
        
        # Resize e Crop
        resized = short_clip.resize(height=target_h)
        if resized.w > target_w:
            final = resized.crop(x_center=resized.w/2, width=target_w)
        else:
            final = resized.resize(width=target_w).crop(y_center=resized.h/2, height=target_h)
        
        out_path = f"temp_viral_{int(time.time())}.mp4"
        # Preset 'ultrafast' per non far timeout sul server
        final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
        return out_path

# --- INTERFACCIA ---
with st.sidebar:
    category = st.selectbox("Cosa hai filmato?", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    platform = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    content_type = st.radio("Tipo di Contenuto", ["Reels", "Storie", "Post"])
    uploaded_files = st.file_uploader("📤 trascina qui i video", type=["mp4", "mov"], accept_multiple_files=True)

# --- PROCESSO ---
if uploaded_files and st.button("✨ GENERA CONTENUTI VIRALI"):
    col_main = st.container()
    
    for uploaded_file in uploaded_files:
        # Usiamo st.status in modo che si chiuda quando finisce
        with st.status(f"🎬 Elaborando: {uploaded_file.name}") as status:
            
            # 1. Salvataggio locale
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_file.read())
            path = tfile.name

            try:
                # 2. Upload Google
                status.update(label="Caricamento su Google AI...")
                video_ai = genai.upload_file(path=path)
                
                # 3. Attesa (Polling)
                start_wait = time.time()
                while True:
                    file_info = genai.get_file(video_ai.name)
                    if file_info.state.name == "ACTIVE":
                        break
                    if time.time() - start_wait > 300: # Timeout 5 minuti
                        raise Exception("Google ci sta mettendo troppo. Riprova con un video più corto.")
                    status.update(label=f"Google sta indicizzando il video ({file_info.state.name})...")
                    time.sleep(5)
                
                # 4. Analisi AI
                status.update(label="L'AI sta scegliendo il momento migliore...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Sei un Social Media Manager per {category}. Analizza questo video per {platform} {content_type}. Trova il momento più virale tra 7 e 12 secondi. Restituisci SOLO JSON: {{'start': sec, 'end': sec, 'hook': 'testo', 'caption': 'testo', 'tags': '#tag', 'reason': 'perché'}}"
                
                response = model.generate_content([video_ai, prompt])
                data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
                
                # 5. Montaggio
                status.update(label="Montaggio video (questo richiede tempo)...")
                final_path = process_video_optimized(path, platform, content_type, data['start'], data['end'])
                
                # 6. Visualizzazione
                with col_main:
                    with st.expander(f"✅ PRONTO: {uploaded_file.name}", expanded=True):
                        c1, c2 = st.columns([1, 1.2])
                        with c1:
                            st.video(final_path)
                            with open(final_path, "rb") as f:
                                st.download_button("📥 SCARICA", f, file_name=f"viral_{uploaded_file.name}")
                        with c2:
                            st.subheader(f"🪝 {data['hook']}")
                            st.write(f"**Strategia:** {data['reason']}")
                            st.code(f"{data['caption']}\n\n{data['tags']}")
                
                status.update(label="Completato!", state="complete")
                
            except Exception as e:
                st.error(f"Errore su {uploaded_file.name}: {e}")
            finally:
                if os.path.exists(path): os.remove(path)
                try: genai.delete_file(video_ai.name)
                except: pass
