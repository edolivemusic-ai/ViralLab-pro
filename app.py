import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re

# Configurazione Pagina
st.set_page_config(page_title="Viral Lab Bari", layout="wide")
st.title("🎬 Puglia Sizzle Lab ☀️")

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Inserisci la chiave API nei Secrets di Streamlit.")
    st.stop()
genai.configure(api_key=api_key)

# Mappa Formati (720p per non far crashare il server)
FMT = {
    "Instagram": (720, 1280),
    "TikTok": (720, 1280),
    "Facebook": (720, 720)
}

with st.sidebar:
    st.header("📍 Configurazione")
    cat = st.selectbox("Tipo Evento", ["DJ Set", "Musica dal Vivo", "Wedding Band", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    files = st.file_uploader("📤 Carica i video", type=["mp4", "mov"], accept_multiple_files=True)

if files and st.button("🚀 GENERA VIDEO FINALE"):
    clips = []
    temp_files = []
    
    try:
        with st.status("Lavorando sui tuoi video...") as status:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            for f in files:
                status.write(f"Analizzando: {f.name}")
                # Salvataggio temporaneo
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read())
                p = t.name
                temp_files.append(p)
                
                # Upload e Analisi AI
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING":
                    time.sleep(3)
                
                # Pausa per evitare errore 404
                time.sleep(10)
                
                prompt = f"Sei un editor a Bari. Trova l'highlight di 2.5s in questo video di {cat}. Rispondi SOLO JSON: {{'start': float}}"
                r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                
                try:
                    data = json.loads(r.text)
                    start_t = float(data['start'])
                    
                    # Caricamento e Taglio immediato (risparmio RAM)
                    target_w, target_h = FMT[plat]
                    with mp.VideoFileClip(p) as video_clip:
                        # Taglio e Resize
                        sub = video_clip.subclip(start_t, min(start_t + 2.5, video_clip.duration)).resize(height=target_h)
                        # Crop centrale
                        if sub.w > target_w:
                            final_sub = sub.crop(x_center=sub.w/2, width=target_w)
                        else:
                            final_sub = sub
                        
                        clips.append(final_sub.copy())
                    status.write(f"✅ Clip {f.name} pronta.")
                except:
                    status.write(f"⚠️ Impossibile trovare highlight in {f.name}, salto...")
                
                # Pulizia file su Google
                genai.delete_file(v_ai.name)

            if clips:
                status.write("🎬 Creazione montaggio finale (Sizzle Reel)...")
                final_video = mp.concatenate_videoclips(clips, method="compose")
                out_path = "video_virale_puglia.mp4"
                final_video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast')
                
                st.video(out_path)
                with open(out_path, "rb") as vf:
                    st.download_button("📥 SCARICA IL VIDEO PRONTO", vf, file_name="bari_viral_reel.mp4")
                st.success("Fatto! Caricalo sui social con un audio trend.")
            else:
                st.error("Non è stato possibile creare nessuna clip. Riprova con video diversi.")

    except Exception as e:
        st.error(f"Errore durante il processo: {e}")
    
    finally:
        # Pulizia totale file temporanei
        for p in temp_files:
            if os.path.exists(p): os.remove(p)
