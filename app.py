import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image

# --- PATCH PER PYTHON 3.14 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Puglia Viral Lab", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:white;}.stButton>button{background:linear-gradient(90deg,#00f2ea,#FF0050);color:white;font-weight:bold;height:50px;border:none;border-radius:10px;width:100%;}</style>", unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab ☀️")

# --- API SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Inserisci la KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

# --- FUNZIONE MONTAGGIO ---
def create_reel(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    for d in data_list:
        try:
            v = mp.VideoFileClip(d['path'])
            # Taglio highlight reale (2.8 secondi per ritmo musicale)
            s = float(d['start'])
            e = min(s + 2.8, v.duration)
            c = v.subclip(s, e).resize(height=th)
            f = c.crop(x_center=c.w/2, width=tw) if c.w > tw else c
            clips.append(f.copy())
            v.close()
        except: continue
    if not clips: return None
    final = mp.concatenate_videoclips(clips, method="compose")
    out = f"reel_{int(time.time())}.mp4"
    final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
    return out

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("📍 Bari/Puglia Setup")
    cat = st.selectbox("Tipo Evento", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica Video Grezzi", type=["mp4", "mov"], accept_multiple_files=True)

# --- LOGICA ---
if files:
    if st.button("🔎 1. TROVA HIGHLIGHTS E MUSICA"):
        all_h = []
        with st.status("🛸 AI sta analizzando i momenti migliori...") as stt:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            for f in files:
                stt.write(f"Scansione: {f.name}")
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read()); p = t.name
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING": time.sleep(4)
                
                time.sleep(12) # Pausa obbligatoria per stabilità Google
                prompt = f"Sei un editor a Bari. Trova il picco di energia (drop, acuto o brindisi) in questo video di {cat}. JSON: {{'start': float, 'music': '3 canzoni trend italia'}}"
                try:
                    r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                    d = json.loads(r.text)
                    d['path'] = p; d['name'] = f.name; all_h.append(d)
                except: pass
            
            st.session_state['h_list'] = all_h
            stt.update(label="Analisi completata!", state="complete")

    if 'h_list' in st.session_state and len(st.session_state['h_list']) > 0:
        st.success(f"🔥 Ho isolato {len(st.session_state['h_list'])} momenti top!")
        st.info(f"🎵 **MUSICA ITALIA SUGGERITA:**\n\n{st.session_state['h_list'][0].get('music','')}")
        
        if st.button("🎬 2. GENERA SUPER-MONTAGGIO FINALE"):
            with st.status("✂️ Montaggio ritmico in corso...") as stt:
                out_path = create_reel(st.session_state['h_list'], plat, ctype)
                if out_path:
                    st.video(out_path)
                    with open(out_path, "rb") as fr:
                        st.download_button("📥 SCARICA VIDEO REEL", fr, file_name="sizzle_puglia.mp4")
                stt.update(label="Fatto!", state="complete")
