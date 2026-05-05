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
st.markdown("<style>.main{background-color:#0f1116;color:#f0f2f6;}.stButton>button{background:linear-gradient(90deg,#FF0050 0%,#00f2ea 100%);color:white;border-radius:10px;width:100%;font-weight:bold;}</style>", unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Super-Montaggio ☀️")

# --- API SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Configura API Key nei Secrets di Streamlit.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

# --- FUNZIONE MONTAGGIO ---
def build_sizzle(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    for d in data_list:
        try:
            v = mp.VideoFileClip(d['path'])
            s, e = float(d['start']), float(d['end'])
            if e <= s: e = s + 2.5
            # Taglio ritmico e resize
            c = v.subclip(s, min(e, s + 2.5)).resize(height=th)
            f = c.crop(x_center=c.w/2, width=tw) if c.w > tw else c
            clips.append(f.copy())
            v.close()
        except Exception as e:
            st.error(f"Errore tecnico montaggio clip: {e}")
    
    if not clips: return None
    
    final = mp.concatenate_videoclips(clips, method="compose")
    out = f"final_puglia_{int(time.time())}.mp4"
    final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
    return out

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("📍 Bari/Puglia Setup")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica Video Grezzi", type=["mp4", "mov"], accept_multiple_files=True)

# --- LOGICA ---
if files:
    if st.button("🔎 1. ANALIZZA HIGHLIGHTS E MUSICA"):
        all_h = []
        music_tip = "Analisi in corso..."
        
        with st.status("🛸 Analisi intelligente dei video...") as stt:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            for f in files:
                stt.write(f"Esaminando: {f.name}...")
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read()); p = t.name
                
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING":
                    time.sleep(3)
                
                time.sleep(12) # Pausa stabilità API
                
                prompt = f"""
                Sei un editor esperto a Bari, Italia. Analizza questo video di {cat}.
                Trova un highlight di 2.5 secondi molto dinamico.
                Suggerisci anche 3 trend musicali italiani attuali.
                RESTITUISCI SOLO JSON:
                {{
                  "start": float,
                  "end": float,
                  "music": "3 canzoni trend italia"
                }}
                """
                
                try:
                    r = model.generate_content([v_ai, prompt])
                    # Estrazione sicura del JSON con Regex
                    match = re.search(r'\{.*\}', r.text, re.DOTALL)
                    if match:
                        d = json.loads(match.group())
                        d['path'] = p; d['name'] = f.name
                        all_h.append(d)
                        music_tip = d.get('music', music_tip)
                    else:
                        st.error(f"L'AI non ha restituito dati validi per {f.name}")
                except Exception as e:
                    st.error(f"Errore AI su {f.name}: {e}")
                
            st.session_state['h_list'] = all_h
            st.session_state['m_adv'] = music_tip
            stt.update(label="Analisi completata con successo!", state="complete")

    if 'h_list' in st.session_state and len(st.session_state['h_list']) > 0:
        st.success(f"✅ Trovati {len(st.session_state['h_list'])} momenti spettacolari!")
        st.info(f"🎵 **TREND MUSICALI SUGGERITI (ITALIA):**\n\n{st.session_state['m_adv']}")
        
        if st.button("🎬 2. GENERA SUPER-MONTAGGIO FINALE"):
            with st.status("✂️ Creando il montaggio ritmico...") as stt:
                final_out = build_sizzle(st.session_state['h_list'], plat, ctype)
                if final_out:
                    st.video(final_out)
                    with open(final_out, "rb") as fr:
                        st.download_button("📥 SCARICA VIDEO COMPLETO", fr, file_name="sizzle_puglia.mp4")
                    stt.update(label="Reel pronto per il download!", state="complete")
    elif 'h_list' in st.session_state:
        st.warning("⚠️ Nessun momento è stato analizzato correttamente. Prova a ricaricare i file.")
