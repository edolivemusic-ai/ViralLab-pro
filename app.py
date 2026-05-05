import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image
from google.api_core import exceptions

# --- 1. PATCH COMPATIBILITÀ ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- 2. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Viral Lab Puglia ☀️", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 12px; font-size: 20px; border-radius: 10px; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("☀️ Music Viral Lab: Bari & Puglia Edition 🌊")
st.subheader("Ottimizzato per eventi in Masseria, Club baresi e Wedding in Puglia")

# --- 3. CONFIGURAZIONE API ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Inserisci la API KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    st.sidebar.success(f"✅ AI Pugliese Pronta: {active_model}")
except Exception as e:
    st.sidebar.error(f"❌ Errore AI: {e}")
    st.stop()

# --- 4. FORMATI SOCIAL ---
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# --- 5. FUNZIONE MONTAGGIO ---
def auto_edit(path, plat, ctype, start, end):
    try:
        with mp.VideoFileClip(path) as video:
            tw, th = FMT[plat][ctype]
            s, e = max(0, float(start)), min(float(end), video.duration)
            if (e - s) < 2: e = s + 10
            clip = video.subclip(s, e).resize(height=th)
            final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            out = f"viral_puglia_{int(time.time())}.mp4"
            final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1, bitrate="2000k")
            return out
    except Exception as ex:
        st.error(f"Errore montaggio: {ex}")
        return None

# --- 6. INTERFACCIA ---
with st.sidebar:
    st.header("📍 Localizzazione: Bari/Puglia")
    cat = st.selectbox("Tipo di Evento", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato Video", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica i video della serata", type=["mp4", "mov"], accept_multiple_files=True)

res_container = st.container()

# --- 7. LOGICA PROCESSO ---
if files and st.button("🔥 CREA CONTENUTO VIRALE PUGLIESE"):
    for f in files:
        with st.status(f"🛠️ Elaborando {f.name}...") as stt:
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name
            v_ai = None
            
            try:
                stt.write("🚀 Upload video...")
                v_ai = genai.upload_file(path=p)
                while True:
                    inf = genai.get_file(v_ai.name)
                    if inf.state.name == "ACTIVE": break
                    time.sleep(5)
                
                stt.write("🧠 L'AI sta studiando il mood barese...")
                time.sleep(15)
                
                model = genai.GenerativeModel(active_model)
                
                # PROMPT LOCALIZZATO: BARI & PUGLIA
                prompt = f"""
                Sei il miglior esperto di comunicazione digitale della PUGLIA, specializzato nel mercato di BARI e provincia.
                Analizza questo video di {cat}. 
                Trova i 10 secondi più potenti che trasmettano l'energia delle feste pugliesi.

                REGOLE PER IL MERCATO PUGLIESE:
                1. La 'caption' deve essere in ITALIANO, con uno stile caldo, solare e coinvolgente tipico del Sud.
                2. Includi riferimenti al mood locale (es. 'il calore della Puglia', 'notti baresi', 'festa in masseria') se coerenti.
                3. Usa hashtags strategici come: #weareinpuglia #bari #puglia #matrimoniopuglia #pugliaview #apulia #volgobari #djsetpuglia.
                4. I 'music' trend devono essere audio popolari in ITALIA, con un occhio ai suoni mediterranei o hit del momento nei club di Bari e provincia.
                
                Rispondi RIGOROSAMENTE in JSON:
                {{
                  "start": float,
                  "end": float,
                  "caption": "stringa virale pugliese",
                  "music": ["canzone trend 1", "canzone trend 2", "canzone trend 3"]
                }}
                """
                
                data = None
                for attempt in range(3):
                    try:
                        resp = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                        data = json.loads(resp.text)
                        break
                    except Exception:
                        time.sleep(20)

                if not data: continue

                stt.write("✂️ Taglio e ottimizzazione formato...")
                out = auto_edit(p, plat, ctype, data['start'], data['end'])
                
                if out:
                    with res_container:
                        st.success(f"✅ {f.name} PRONTO PER IL FEED!")
                        c1, c2 = st.columns([1, 1.3])
                        with c1:
                            st.video(out)
                            with open(out, "rb") as o_f:
                                st.download_button(f"📥 SCARICA VIDEO", o_f, file_name=f"viral_bari_{f.name}")
                        with c2:
                            st.info(f"**Caption per Bari/Puglia:**\n\n{data['caption']}")
                            st.warning("**🎵 Trend Musicali consigliati:**\n\n" + "\n".join([f"- {m}" for m in data.get('music', [])]))
                
                stt.update(label=f"Video {f.name} ottimizzato per la Puglia!", state="complete")

            except Exception as err:
                st.error(f"Errore: {err}")
            finally:
                if os.path.exists(p): os.remove(p)
                if v_ai:
                    try: genai.delete_file(video_ai.name)
                    except: pass
