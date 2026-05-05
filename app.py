import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, re, time
import PIL.Image
from google.api_core import exceptions

# --- PATCH PYTHON 3.14 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Puglia Sizzle Lab", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:#f0f2f6;}.stButton>button{background:linear-gradient(90deg,#FF0050 0%,#00f2ea 100%);color:white;border-radius:10px;width:100%;}</style>", unsafe_allow_html=True)
st.title("🎬 Puglia Sizzle Lab: Super-Montaggio ☀️")

# --- API SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Configura API Key nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280)}
}

# --- FUNZIONE MONTAGGIO RITMICO ---
def build_sizzle(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    for d in data_list:
        try:
            with mp.VideoFileClip(d['path']) as v:
                s, e = float(d['start']), float(d['end'])
                # Taglio ritmico (max 2.5s per clip)
                c = v.subclip(s, min(e, s + 2.5)).resize(height=th)
                f = c.crop(x_center=c.w/2, width=tw) if c.w > tw else c
                clips.append(f.copy())
        except: continue
    if not clips: return None
    final = mp.concatenate_videoclips(clips, method="compose")
    out = f"sizzle_{int(time.time())}.mp4"
    final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
    return out

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("📍 Bari/Puglia Setup")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Post"])
    files = st.file_uploader("📤 Carica Video Grezzi", type=["mp4", "mov"], accept_multiple_files=True)

# --- LOGICA ---
if files:
    if st.button("🔎 1. ANALIZZA HIGHLIGHTS E MUSICA"):
        all_h = []
        with st.status("🛸 AI sta visionando i file...") as stt:
            for f in files:
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read()); p = t.name
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING": time.sleep(4)
                time.sleep(10)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Expert editor in Bari, Italy. Find 3s highlight for {cat}. JSON: {{'start':float, 'end':float}}"
                try:
                    r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                    d = json.loads(r.text)
                    d['path'] = p; d['name'] = f.name; all_h.append(d)
                except: pass
            st.session_state['h_list'] = all_h
            m_p = f"Suggerisci 3 trend musicali Italia/Puglia per montaggio {cat} ritmico."
            st.session_state['m_adv'] = model.generate_content(m_p).text
            stt.update(label="Analisi completata!", state="complete")

    if 'h_list' in st.session_state:
        st.success(f"Trovati {len(st.session_state['h_list'])} momenti top!")
        st.warning(f"🎵 **CONSIGLI MUSICA ITALIA:**\n\n{st.session_state['m_adv']}")
        
        if st.button("🎬 2. GENERA SUPER-MONTAGGIO FINALE"):
            with st.status("✂️ Montaggio ritmico in corso...") as stt:
                final_out = build_sizzle(st.session_state['h_list'], plat, ctype)
                if final_out:
                    st.video(final_out)
                    with open(final_out, "rb") as fr:
                        st.download_button("📥 SCARICA REEL FINALE", fr, file_name="sizzle_puglia.mp4")
                stt.update(label="Fatto!", state="complete")
