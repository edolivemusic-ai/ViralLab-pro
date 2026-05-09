import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time, re
import PIL.Image

# --- PATCH COMPATIBILITÀ PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Puglia Viral Lab Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: white; }
    .stButton>button { 
        background: linear-gradient(90deg, #00f2ea, #FF0050); 
        color: white; border: none; border-radius: 10px; height: 55px; width: 100%; font-weight: bold;
    }
    .stExpander { background-color: #1e2129; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Highlight Editor ☀️")

# --- API ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

# --- FUNZIONE RENDERING RITMICO ---
def create_sizzle(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    progress_bar = st.progress(0)
    
    for i, d in enumerate(data_list):
        try:
            v = mp.VideoFileClip(d['path'])
            s = float(d['start'])
            # Taglio ritmico professionale: 2.8 secondi
            e = min(s + 2.8, v.duration)
            
            clip = v.subclip(s, e).resize(height=th)
            final_clip = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            # Aggiungiamo una dissolvenza incrociata mini
            clips.append(final_clip.copy().fadein(0.2).fadeout(0.2))
            v.close()
        except: continue
        progress_bar.progress((i + 1) / len(data_list))

    if not clips: return None
    
    # Unione clip
    sizzle = mp.concatenate_videoclips(clips, method="compose")
    out = f"puglia_sizzle_{int(time.time())}.mp4"
    sizzle.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
    return out

# --- INTERFACCIA ---
with st.sidebar:
    st.header("📍 Bari/Puglia Config")
    cat = st.selectbox("Tipo Contenuto", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("📤 Carica i video grezzi", type=["mp4", "mov"], accept_multiple_files=True)

# --- LOGICA ---
if files:
    if st.button("🔎 1. SCANSIONA HIGHLIGHTS ED ENERGIA"):
        all_h = []
        with st.status("🛸 AI sta cercando i momenti più forti...") as stt:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            for f in files:
                stt.write(f"Scansione: {f.name}")
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                t.write(f.read()); p = t.name
                
                v_ai = genai.upload_file(path=p)
                while genai.get_file(v_ai.name).state.name == "PROCESSING": time.sleep(4)
                
                time.sleep(12) # Sicurezza API
                prompt = f"""
                Sei un video editor a Bari. Trova il momento di picco (drop, brindisi, emozione) in questo video di {cat}. 
                Rispondi SOLO JSON: {{'start': float, 'reason': 'string', 'music': '3 trend italia'}}
                """
                try:
                    r = model.generate_content([v_ai, prompt], generation_config={"response_mime_type": "application/json"})
                    d = json.loads(r.text)
                    d.update({'path': p, 'name': f.name})
                    all_h.append(d)
                except: pass
            
            st.session_state['h_list'] = all_h
            stt.update(label="Analisi completata!", state="complete")

    if 'h_list' in st.session_state and st.session_state['h_list']:
        st.success(f"🔥 Isolati {len(st.session_state['h_list'])} highlights!")
        
        # Preview Highlights
        with st.expander("👀 Vedi cosa ho scelto per Bari/Puglia"):
            for h in st.session_state['h_list']:
                st.write(f"✅ **{h['name']}**: {h.get('reason','Highlight trovato')} al sec. {h['start']}")
        
        st.info(f"🎵 **MUSICA SUGGERITA:** {st.session_state['h_list'][0].get('music','')}")
        
        if st.button("🎬 2. GENERA MONTAGGIO FINALE"):
            with st.status("✂️ Montaggio ritmico in corso...") as stt:
                final_video = create_sizzle(st.session_state['h_list'], plat, ctype)
                if final_video:
                    st.video(final_video)
                    with open(final_video, "rb") as fr:
                        st.download_button("📥 SCARICA VIDEO PRONTO", fr, file_name="bari_sizzle_pro.mp4")
                stt.update(label="Reel completato!", state="complete")
