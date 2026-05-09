import streamlit as st
import google.generativeai as genai
from moviepy import VideoFileClip, concatenate_videoclips
import tempfile, os, json, time

st.set_page_config(page_title="Viral Lab Bari", layout="wide")
st.title("🎬 Puglia Viral Lab ☀️")

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca API KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

# Forza il rilevamento del modello corretto per evitare il 404
def get_model_name():
    try:
        for m in genai.list_models():
            if 'gemini-1.5-flash' in m.name and 'generateContent' in m.supported_generation_methods:
                return m.name
    except:
        return 'models/gemini-1.5-flash'

MODEL_NAME = get_model_name()

with st.sidebar:
    st.header("📍 Bari/Puglia Config")
    cat = st.selectbox("Evento", ["DJ Set", "Wedding Band", "Musica Live", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    files = st.file_uploader("📤 Carica Video della serata", type=["mp4", "mov"], accept_multiple_files=True)

if files and st.button("🚀 GENERA SUPER-MONTAGGIO"):
    final_clips = []
    temp_paths = []
    
    with st.status("🛠️ Lavorando sui tuoi highlights...") as status:
        model = genai.GenerativeModel(MODEL_NAME)
        
        for f in files:
            status.write(f"Analizzando: {f.name}")
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name
            temp_paths.append(p)
            
            try:
                # 1. Upload e Polling Google
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING":
                    time.sleep(5)
                
                # Attesa di sicurezza per indicizzazione Google
                time.sleep(15) 
                
                prompt = f"""
                Sei un editor a Bari. Trova il momento di picco in questo {cat} (drop, brindisi o climax).
                Suggerisci anche 3 trend musicali Italia.
                Ritorna SOLO JSON: {{"start": float, "music": "string"}}
                """
                
                r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                res = json.loads(r.text)
                
                # 2. Montaggio con nuova sintassi MoviePy 2.1
                with VideoFileClip(p) as video:
                    start_t = float(res['start'])
                    # Taglio ritmico 2.2 secondi
                    sub = video.subclipped(start_t, min(start_t + 2.2, video.duration))
                    # Adattamento 720p per stabilità server
                    sub_r = sub.resized(height=1280)
                    if sub_r.w > 720:
                        sub_f = sub_r.cropped(center_x=sub_r.w/2, width=720)
                    else:
                        sub_f = sub_r
                    
                    final_clips.append(sub_f.with_effects([]))
                
                status.write(f"✅ Highlight {f.name} salvato.")
                st.session_state['music'] = res['music']
                genai.delete_file(v_ai.name)
                
            except Exception as e:
                status.write(f"⚠️ Salto {f.name}: {e}")

        if final_clips:
            status.write("🎬 Esportazione Reel finale...")
            result = concatenate_videoclips(final_clips, method="compose")
            out = "final_puglia.mp4"
            result.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast')
            
            st.success("✨ REEL PRONTO PER BARI E PROVINCIA!")
            st.video(out)
            st.info(f"🎵 **Musica Trend Italia:** {st.session_state.get('music', '')}")
            with open(out, "rb") as vf:
                st.download_button("📥 SCARICA VIDEO", vf, file_name="bari_reel.mp4")
        else:
            st.error("Nessun momento trovato. Ricarica video più incisivi.")

    for p in temp_paths:
        if os.path.exists(p): os.remove(p)
