import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image

# --- PATCH PER PILLOW (PYTHON 3.14) ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Viral Lab Bari", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:white;}.stButton>button{background:linear-gradient(90deg,#00f2ea,#FF0050);color:white;font-weight:bold;height:55px;border:none;border-radius:12px;width:100%;}</style>", unsafe_allow_html=True)

st.title("🎬 Puglia Viral Lab: Highlights ☀️")

# API
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca API KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

# Formati (Risoluzione 720p per stabilità)
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

with st.sidebar:
    st.header("📍 Bari/Puglia Lab")
    cat = st.selectbox("Evento", ["DJ Set", "Musica Live", "Wedding Music", "Wedding Band", "Karaoke"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Video grezzi", type=["mp4", "mov"], accept_multiple_files=True)

if files and st.button("🔥 CREA REEL HIGHLIGHTS"):
    clips = []
    temp_paths = []
    
    with st.status("🚀 Avvio Laboratorio Virale...") as status:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        for f in files:
            status.write(f"Scansione: {f.name}")
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read()); p = t.name
            temp_paths.append(p)
            
            # AI Analisi Highlights
            v_ai = genai.upload_file(path=p)
            while genai.get_file(v_ai.name).state.name == "PROCESSING": time.sleep(4)
            time.sleep(12)
            
            prompt = f"Sei un regista a Bari. Trova il momento più forte di 2.5s in questo video di {cat}. Ritorna SOLO JSON: {{'start': float, 'music': '3 trend italia'}}"
            try:
                r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                d = json.loads(r.text)
                
                # Montaggio al volo della clip
                tw, th = FMT[plat][ctype]
                with mp.VideoFileClip(p) as video:
                    st_t = float(d['start'])
                    sub = video.subclip(st_t, min(st_t + 2.5, video.duration)).resize(height=th)
                    final_sub = sub.crop(x_center=sub.w/2, width=tw) if sub.w > tw else sub
                    clips.append(final_sub.copy())
                status.write(f"✅ Highlight {f.name} isolato.")
                st.session_state['last_music'] = d['music']
            except:
                status.write(f"❌ Errore su {f.name}, salto...")
            
            genai.delete_file(v_ai.name)

        if clips:
            status.write("🎬 Unione clip e rendering finale...")
            final_video = mp.concatenate_videoclips(clips, method="compose")
            out_p = f"puglia_reel_{int(time.time())}.mp4"
            final_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
            
            st.success("✨ REEL PRONTO PER BARI E PROVINCIA!")
            st.video(out_p)
            st.info(f"🎵 **Musica Consigliata:** {st.session_state.get('last_music', 'Trend TikTok Italia')}")
            with open(out_p, "rb") as vf:
                st.download_button("📥 SCARICA IL VIDEO", vf, file_name="bari_reel.mp4")
        else:
            st.error("Nessun momento rilevato. Riprova con altri video.")

    # Pulizia
    for p in temp_paths: 
        if os.path.exists(p): os.remove(p)
