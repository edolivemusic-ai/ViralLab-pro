import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Music Viral Lab Pro", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:#f0f2f6;}.stButton>button{background:linear-gradient(90deg,#FF0050 0%,#00f2ea 100%);color:white;border-radius:10px;width:100%;}</style>", unsafe_allow_html=True)
st.title("🎙️ Music Viral Lab")

# --- API ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Inserisci la API KEY nei Secrets.")
    st.stop()

# Configurazione API con gestione errore 404
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

def auto_edit(path, plat, ctype, start, end):
    try:
        with mp.VideoFileClip(path) as video:
            tw, th = FMT[plat][ctype]
            s, e = max(0, float(start)), min(float(end), video.duration)
            if (e - s) < 1: e = s + 10
            clip = video.subclip(s, e).resize(height=th)
            final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            out = f"v_{int(time.time())}.mp4"
            final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1, bitrate="2000k")
            return out
    except Exception as ex:
        st.error(f"Errore tecnico montaggio: {ex}")
        return None

with st.sidebar:
    st.header("Impostazioni")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

if files and st.button("✨ GENERA VIDEO"):
    for f in files:
        t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        t.write(f.read())
        p = t.name
        v_ai = None
        
        try:
            with st.status(f"Lavorando su {f.name}...") as stt:
                stt.write("🛰️ Caricamento su Google AI...")
                v_ai = genai.upload_file(path=p)
                
                while True:
                    inf = genai.get_file(v_ai.name)
                    if inf.state.name == "ACTIVE": break
                    time.sleep(5)
                
                stt.write("🧠 L'AI sta analizzando il contenuto...")
                time.sleep(8)
                
                # Utilizziamo il nome modello aggiornato per evitare il 404
                model = genai.GenerativeModel(model_name='gemini-1.5-flash')
                
                prompt = f"""
                Agisci come esperto Social Media per {cat}. Trova i 10 secondi più virali.
                Rispondi RIGOROSAMENTE in formato JSON:
                {{
                  "start": float,
                  "end": float,
                  "caption": "stringa con hashtag",
                  "music_trends": ["nome canzone 1", "nome canzone 2", "nome canzone 3"]
                }}
                """
                
                resp = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                data = json.loads(resp.text)
                
                stt.write(f"✂️ Rendering {plat}...")
                out = auto_edit(p, plat, ctype, data['start'], data['end'])
                
                if out:
                    st.success(f"✅ {f.name} Pronto!")
                    c1, c2 = st.columns([1, 1.3])
                    with c1: st.video(out)
                    with c2:
                        st.info(f"**Caption:**\n{data['caption']}")
                        st.warning("**🎵 Audio Trend Consigliati:**\n\n" + "\n".join([f"- {m}" for m in data['music_trends']]))
                        with open(out, "rb") as o_f:
                            st.download_button(f"Scarica {f.name}", o_f, file_name=f"viral_{f.name}")
                stt.update(label="Fatto!", state="complete")
                
        except Exception as err:
            st.error(f"Errore: {err}")
        finally:
            if os.path.exists(p): os.remove(p)
            if v_ai:
                try: genai.delete_file(v_ai.name)
                except: pass
