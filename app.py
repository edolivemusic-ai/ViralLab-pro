import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image
from google.api_core import exceptions

# --- 1. PATCH COMPATIBILITÀ (Per Python 3.14 e MoviePy) ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- 2. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Music Viral Lab Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #f0f2f6; }
    .stButton>button { 
        background: linear-gradient(90deg, #FF0050 0%, #00f2ea 100%); 
        color: white; border: none; padding: 12px; font-size: 20px; border-radius: 10px; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Music Viral Lab: Pro Edition")

# --- 3. CONFIGURAZIONE API & MODELLI ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Inserisci la API KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# Trova automaticamente il miglior modello disponibile per il tuo account
try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if 'models/gemini-1.5-flash' in available_models:
        active_model = 'models/gemini-1.5-flash'
    elif 'models/gemini-1.5-pro' in available_models:
        active_model = 'models/gemini-1.5-pro'
    else:
        active_model = available_models[0]
    st.sidebar.success(f"✅ AI Pronta: {active_model}")
except Exception as e:
    st.sidebar.error(f"❌ Errore connessione AI: {e}")
    st.stop()

# --- 4. FORMATI SOCIAL (Ottimizzati 720p per RAM) ---
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# --- 5. FUNZIONE MONTAGGIO AUTOMATICO ---
def auto_edit(path, plat, ctype, start, end):
    try:
        with mp.VideoFileClip(path) as video:
            tw, th = FMT[plat][ctype]
            s = max(0, float(start))
            e = min(float(end), video.duration)
            if (e - s) < 2: e = s + 10
            
            # Taglio e ridimensionamento
            clip = video.subclip(s, e).resize(height=th)
            final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            
            out = f"viral_output_{int(time.time())}.mp4"
            final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1, bitrate="2000k")
            return out
    except Exception as ex:
        st.error(f"Errore tecnico montaggio: {ex}")
        return None

# --- 6. INTERFACCIA UTENTE ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica Video (anche multipli)", type=["mp4", "mov"], accept_multiple_files=True)

res_container = st.container()

# --- 7. LOGICA DI ELABORAZIONE ---
if files and st.button("✨ GENERA VIDEO VIRALI"):
    for f in files:
        with st.status(f"🎬 Elaborando {f.name}...") as stt:
            # Salvataggio temporaneo locale
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            t.write(f.read())
            p = t.name
            v_ai = None
            
            try:
                # A. Upload su Google AI
                stt.write("🛰️ Upload su Google AI...")
                v_ai = genai.upload_file(path=p)
                
                # B. Attesa che il video sia attivo
                while True:
                    inf = genai.get_file(v_ai.name)
                    if inf.state.name == "ACTIVE": break
                    time.sleep(5)
                
                # C. Pausa Anti-404 e Anti-429
                stt.write("🧠 Sincronizzazione AI (Pausa di sicurezza)...")
                time.sleep(15)
                
                # D. Analisi AI con Retry per Quota
                model = genai.GenerativeModel(active_model)
                prompt = f"""
                Agisci come esperto Social Media per {cat}. Trova i 10 secondi più virali.
                Identifica il drop, l'emozione o il momento clou.
                Rispondi RIGOROSAMENTE in formato JSON:
                {{
                  "start": float,
                  "end": float,
                  "caption": "stringa virale per {plat}",
                  "music": ["canzone trend 1", "canzone trend 2", "canzone trend 3"]
                }}
                """
                
                data = None
                for attempt in range(3):
                    try:
                        resp = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                        data = json.loads(resp.text)
                        break
                    except exceptions.ResourceExhausted:
                        stt.write(f"⚠️ Limite quota raggiunto. Attendo 30s (Tentativo {attempt+1})...")
                        time.sleep(30)
                    except exceptions.NotFound:
                        stt.write(f"⚠️ Sincronizzazione fallita. Riprovo tra 10s...")
                        time.sleep(10)

                if not data:
                    st.error(f"Impossibile analizzare {f.name} dopo vari tentativi.")
                    continue

                # E. Rendering Fisico
                stt.write(f"✂️ Taglio e Formattazione per {plat}...")
                out = auto_edit(p, plat, ctype, data['start'], data['end'])
                
                if out:
                    with res_container:
                        st.success(f"✅ {f.name} PRONTO!")
                        c1, c2 = st.columns([1, 1.3])
                        with c1:
                            st.video(out)
                            with open(out, "rb") as o_f:
                                st.download_button(f"📥 SCARICA {f.name}", o_f, file_name=f"viral_{f.name}")
                        with c2:
                            st.info(f"**Caption consigliata:**\n\n{data['caption']}")
                            st.warning("**🎵 Audio Trend Consigliati:**\n\n" + "\n".join([f"- {m}" for m in data.get('music', [])]))
                
                stt.update(label=f"Video {f.name} completato!", state="complete")

            except Exception as err:
                st.error(f"Errore su {f.name}: {err}")
            finally:
                # Pulizia totale
                if os.path.exists(p): os.remove(p)
                if v_ai:
                    try: genai.delete_file(v_ai.name)
                    except: pass
