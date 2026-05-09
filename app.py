import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image

# --- CORREZIONE COMPATIBILITÀ PYTHON 3.14 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Puglia Sizzle Lab Pro", layout="wide")
st.markdown("""<style>.main{background-color:#0f1116;color:white;}.stButton>button{background:linear-gradient(90deg,#00f2ea,#FF0050);color:white;border:none;border-radius:10px;height:55px;width:100%;font-weight:bold;}</style>""", unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Il Regista AI ☀️")
st.markdown("---")

# --- API SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

# --- RENDERING RITMICO (Sincronizzato 2.14s) ---
def build_sizzle_master(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    pb = st.progress(0)
    for i, d in enumerate(data_list):
        try:
            with mp.VideoFileClip(d['path']) as v:
                start_h = float(d['start'])
                # 2.14 secondi è la misura perfetta per il beat matching
                end_h = min(start_h + 2.14, v.duration)
                clip = v.subclip(start_h, end_h).resize(height=th)
                final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
                clips.append(final.copy().fadein(0.1).fadeout(0.1))
            pb.progress((i + 1) / len(data_list))
        except: continue
    
    if not clips: return None
    sizzle = mp.concatenate_videoclips(clips, method="compose")
    out = f"puglia_reel_{int(time.time())}.mp4"
    sizzle.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
    return out

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("📍 Bari/Puglia Control")
    cat = st.selectbox("Tipo Evento", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica i video grezzi", type=["mp4", "mov"], accept_multiple_files=True)

# --- WORKFLOW ---
if files:
    if st.button("🔎 1. SCANSIONA HIGHLIGHTS E TROVA MUSICA"):
        highlights = []
        with st.status("🛸 AI sta analizzando i momenti più forti...") as stt:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            for f in files:
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read()); p = t.name
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING": time.sleep(4)
                
                time.sleep(12) # Pausa critica stabilità Google
                prompt = f"""
                Sei un video editor esperto a Bari. Analizza questo video di {cat}.
                Trova l'highlight esatto di 2 secondi (drop, climax, brindisi).
                Suggerisci anche 3 trend musicali Italia.
                RISPONDI SOLO JSON: {{"start": float, "reason": "string", "music": "string"}}
                """
                try:
                    r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                    d = json.loads(r.text)
                    d.update({'path': p, 'name': f.name})
                    highlights.append(d)
                except: pass
            
            st.session_state['h_list'] = highlights
            stt.update(label="Analisi completata!", state="complete")

    if 'h_list' in st.session_state and st.session_state['h_list']:
        st.success(f"🔥 Ho isolato {len(st.session_state['h_list'])} clip spettacolari!")
        st.info(f"🎵 **MUSICA SUGGERITA:** {st.session_state['h_list'][0].get('music','')}")
        
        if st.button("🎬 2. GENERA MONTAGGIO A TEMPO"):
            with st.status("✂️ Montaggio ritmico in corso...") as stt:
                final = build_sizzle_master(st.session_state['h_list'], plat, ctype)
                if final:
                    st.video(final)
                    with open(final, "rb") as fr:
                        st.download_button("📥 SCARICA REEL FINALE", fr, file_name="bari_viral_reel.mp4")
                stt.update(label="Reel completato!", state="complete")
