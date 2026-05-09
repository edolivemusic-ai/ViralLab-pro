import streamlit as st
import google.generativeai as genai
from moviepy import VideoFileClip, concatenate_videoclips
import tempfile, os, json, time

# Configurazione Pagina
st.set_page_config(page_title="Viral Lab Puglia v2", layout="wide")
st.title("🎬 Puglia Viral Lab: Sizzle Reel ☀️")

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Inserisci la KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

# Formato Reels 720p
W_TARGET, H_TARGET = 720, 1280

with st.sidebar:
    st.header("📍 Bari/Puglia")
    cat = st.selectbox("Evento", ["DJ Set", "Wedding Band", "Musica Live", "Karaoke"])
    files = st.file_uploader("📤 Carica i video della serata", type=["mp4", "mov"], accept_multiple_files=True)

if files and st.button("🚀 GENERA SUPER-MONTAGGIO"):
    final_clips = []
    temp_paths = []
    
    with st.status("🛸 Analisi e Montaggio in corso...") as status:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        for f in files:
            status.write(f"Scansione highlight: {f.name}")
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name
            temp_paths.append(p)
            
            try:
                # 1. AI Analysis
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING":
                    time.sleep(4)
                time.sleep(12) # Pausa stabilità Google
                
                prompt = f"Sei un editor a Bari. Trova l'highlight di 2.5s in questo {cat}. JSON: {{'start': float}}"
                r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                start_t = json.loads(r.text)['start']
                
                # 2. MoviePy 2.0 Editing (Nuova Sintassi)
                with VideoFileClip(p) as video:
                    # Taglio ritmico
                    sub = video.subclipped(start_t, min(start_t + 2.5, video.duration))
                    # Resize e Crop per Reels
                    sub_r = sub.resized(height=H_TARGET)
                    if sub_r.w > W_TARGET:
                        sub_f = sub_r.cropped(center_x=sub_r.w/2, width=W_TARGET)
                    else:
                        sub_f = sub_r
                    
                    final_clips.append(sub_f.with_effects([])) # Copy clip
                
                status.write(f"✅ Highlight {f.name} salvato.")
                genai.delete_file(v_ai.name)
                
            except Exception as e:
                status.write(f"⚠️ Errore su {f.name}: {e}")

        if final_clips:
            status.write("🎬 Esportazione Reel finale...")
            result = concatenate_videoclips(final_clips, method="compose")
            out_name = "puglia_reel_final.mp4"
            # Parametri ultra-leggeri per non far crashare il server
            result.write_videofile(out_name, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast')
            
            st.success("✨ REEL PRONTO PER I SOCIAL!")
            st.video(out_name)
            with open(out_name, "rb") as vf:
                st.download_button("📥 SCARICA IL VIDEO", vf, file_name="bari_reel.mp4")
        else:
            st.error("Nessun momento trovato. Riprova con altri file.")

    # Pulizia
    for p in temp_paths:
        if os.path.exists(p): os.remove(p)
