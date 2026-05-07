import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
from moviepy.config import change_settings
import tempfile
import os
import json
import time
import concurrent.futures
import PIL.Image
import numpy as np

# Patch per ImageMagick
if os.path.exists("/usr/bin/convert"):
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide")

# --- CONFIGURAZIONE API ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()

# Forziamo REST per stabilità su Streamlit Cloud
genai.configure(api_key=api_key, transport='rest')

# --- RILEVATORE DINAMICO DI MODELLI ---
# Questa funzione interroga Google e trova il nome ESATTO che la tua chiave supporta
@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() 
                  if 'generateContent' in m.supported_generation_methods 
                  and 'flash' in m.name.lower()]
        if models:
            return models[0] # Prende il primo modello Flash disponibile (es. models/gemini-1.5-flash)
        return "models/gemini-1.5-flash" # Fallback estremo
    except Exception as e:
        st.warning(f"Errore scansione modelli: {e}")
        return "models/gemini-1.5-flash"

# Troviamo il modello una volta sola
WORKING_MODEL = get_working_model()

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 720)}
}

# ─────────────────────────────────────────
# FUNZIONI CORE
# ─────────────────────────────────────────

def get_audio_peak(video_path, start_hint=0.0):
    try:
        v = mp.VideoFileClip(video_path)
        if not v.audio: return start_hint
        step = 0.5
        ts = np.arange(0, max(0, v.duration - step), step)
        rms = [np.sqrt(np.mean(v.audio.subclip(t, min(t + step, v.duration)).to_soundarray(fps=22050)**2)) for t in ts]
        v.close()
        idx_s = int(max(0, start_hint - 5) / step)
        idx_e = int(min(len(rms), (start_hint + 5) / step))
        return float(ts[idx_s + np.argmax(rms[idx_s:idx_e])])
    except: return start_hint

def scan_single_video(f, cat, model_name):
    p = ""
    v_ai = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
            t.write(f.getvalue())
            p = t.name
        
        v_ai = genai.upload_file(path=p)
        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(2)
        
        model = genai.GenerativeModel(model_name)
        prompt = f"Analizza video {cat}. Trova picco energetico. Rispondi SOLO JSON: {{\"start\": float, \"reason\": string}}"
        
        r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
        d = json.loads(r.text)
        
        start_t = get_audio_peak(p, float(d.get('start', 0)))
        return {'start': start_t, 'path': p, 'name': f.name, 'include': True, 'reason': d.get('reason','')}
    except Exception as err:
        if p and os.path.exists(p): os.unlink(p)
        return {'error': str(err), 'name': f.name}
    finally:
        if v_ai:
            try: genai.delete_file(v_ai.name)
            except: pass

def render_sizzle(data, plat, ctype, dur, audio_p):
    try:
        tw, th = FMT[plat][ctype]
        clips = []
        for d in data:
            v = mp.VideoFileClip(d['path'])
            c = v.subclip(d['start'], min(d['start'] + dur, v.duration)).resize(height=th)
            if c.w > tw: c = c.crop(x_center=c.w/2, width=tw)
            clips.append(c.fadein(0.2).fadeout(0.2))
        
        final = mp.concatenate_videoclips(clips, method="compose")
        if audio_p:
            bg = mp.AudioFileClip(audio_p).subclip(0, final.duration).audio_fadeout(2)
            final.audio = mp.CompositeAudioClip([bg.volumex(0.7), final.audio.volumex(0.3)]) if final.audio else bg
        
        out = f"final_{int(time.time())}.mp4"
        final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
        return out
    except Exception as e:
        st.error(f"Errore render: {e}"); return None

# ─────────────────────────────────────────
# UI
# ─────────────────────────────────────────

st.title("🎬 Puglia Sizzle Lab ☀️")
st.info(f"📡 Modello rilevato e attivo: `{WORKING_MODEL}`")

with st.sidebar:
    st.header("📍 Opzioni")
    cat = st.selectbox("Evento", ["DJ Set", "Wedding Puglia", "Live Music"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    dur = st.slider("Durata clip (s)", 1.0, 5.0, 2.5)
    audio_up = st.file_uploader("Audio (MP3)", type=["mp3"])
    files = st.file_uploader("Video (Max 10)", type=["mp4"], accept_multiple_files=True)

if files:
    if st.button("🔎 1. SCANSIONA VIDEO"):
        results = []
        with st.status("Analisi AI...") as status:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Passiamo il nome del modello rilevato dinamicamente
                futures = [executor.submit(scan_single_video, f, cat, WORKING_MODEL) for f in files[:10]]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    results.append(res)
                    if 'error' in res: st.error(f"❌ {res['name']}: {res['error']}")
                    else: st.write(f"✅ {res['name']} OK")
        st.session_state['h_list'] = results

    if 'h_list' in st.session_state:
        valid = [h for h in st.session_state['h_list'] if 'error' not in h]
        if valid:
            with st.expander("✏️ Modifica Highlights", expanded=True):
                for i, h in enumerate(valid):
                    c1, c2, c3 = st.columns([1, 2, 2])
                    h['include'] = c1.checkbox("Usa", value=True, key=f"c{i}")
                    h['start'] = c2.number_input("Inizio (s)", value=float(h['start']), key=f"s{i}")
                    c3.caption(h.get('reason', ''))

            if st.button("🎬 2. GENERA MONTAGGIO"):
                ap = None
                if audio_up:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as af:
                        af.write(audio_up.getvalue()); ap = af.name
                
                with st.spinner("Creazione video..."):
                    fp = render_sizzle([h for h in valid if h['include']], plat, ctype, dur, ap)
                
                if fp:
                    st.video(fp)
                    st.download_button("📥 Scarica Video", open(fp, "rb"), file_name="sizzle.mp4")

if st.sidebar.button("🧹 Reset"):
    st.session_state.clear(); st.rerun()
