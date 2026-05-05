import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time
from google.api_core import exceptions

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Music Viral Lab Pro", layout="wide")

st.markdown("""<style>.main { background-color: #0f1116; color: #f0f2f6; }
.stButton>button { background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
color: white; border: none; border-radius: 10px; width: 100%; }</style>""", unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Configura GEMINI_API_KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FORMAT_MAP = {
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)},
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

# --- FUNZIONE MONTAGGIO ---
def auto_edit(path, plat, ctype, start, end):
    try:
        with mp.VideoFileClip(path) as video:
            tw, th = FORMAT_MAP[plat][ctype]
            s = max(0, float(start))
            e = min(float(end), video.duration)
            if e <= s: e = s + 10 # Sicurezza durata
            
            clip = video.subclip(s, e).resize(height=th)
            final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            out = f"final_{int(time.time())}.mp4"
            final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
            return out
    except Exception as e:
        st.error(f"Errore tecnico nel montaggio: {e}")
        return None

# --- INTERFACCIA ---
with st.sidebar:
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

res_cons = st.container()

if files and st.button("✨ GENERA VIDEO"):
    for f in files:
        t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        t.write(f.read())
        p = t.name
        v_ai = None
        try:
            with st.status(f"Analizzando {f.name}...") as stt:
                v_ai = genai.upload_file(path=p)
                while True:
                    inf = genai.get_file(v_ai.name)
                    if inf.state.name == "ACTIVE": break
                    time.sleep(5)
                
                time.sleep(12) # Pausa estesa per stabilità
                
                # CONFIGURAZIONE MODELLO PER RISPOSTA JSON PURA
                model = genai.GenerativeModel(
                    model_name='gemini-1.5-flash',
                    generation_config={"response_mime_type": "application/json"}
                )
                
                prompt = f"""
                Sei un esperto video editor per {cat}. Trova la clip più virale (7-12 secondi).
                Ritorna un oggetto JSON con queste chiavi esatte:
                "start": (numero secondi),
                "end": (numero secondi),
                "caption": "testo virale per {plat}"
                """
                
                data = None
                for att in range(4):
                    try:
                        resp = model.generate_content([v_ai, prompt])
                        data = json.loads(resp.text)
                        break
                    except (exceptions.NotFound, json.JSONDecodeError):
                        stt.update(label=f"Sincronizzazione in corso... ({att+1})")
                        time.sleep(10)
                
                if not data:
                    st.error(f"L'AI non è riuscita a generare i tempi per {f.name}")
                    continue

                stt.update(label="Montaggio fisico in corso...")
                out = auto_edit(p, plat, ctype, data['start'], data['end'])
                
                if out:
                    with res_cons:
                        st.success(f"✅ {f.name} PRONTO")
                        c1, c2 = st.columns(2)
                        with c1: st.video(out)
                        with c2: 
                            st.code(data['caption'])
                            with open(out, "rb") as o_file:
                                st.download_button(f"Scarica {f.name}", o_file, fil
