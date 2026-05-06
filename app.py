import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import time

import PIL.Image

# --- PATCH COMPATIBILITÀ ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURAZIONE STREAMLIT ---
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

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- FORMATI ---
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook": {"Post": (720, 720), "Reels": (720, 1280), "Storie": (720, 1280)}
}

# --- FUNZIONI ---
def save_uploaded_file(uploaded_file):
    """Salva il file caricato e restituisce il percorso temporaneo"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(uploaded_file.getvalue())
        return t.name

def create_sizzle(data_list, plat, ctype):
    tw, th = FMT[plat][ctype]
    clips = []
    progress_bar = st.progress(0)
   
    for i, d in enumerate(data_list):
        try:
            v = mp.VideoFileClip(d['path'])
            s = float(d.get('start', 0))
            e = min(s + 2.8, v.duration)
           
            clip = v.subclip(s, e).resize(height=th)
            # Crop centrale se necessario
            final_clip = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            
            # Effetto transizione morbida
            final_clip = final_clip.fadein(0.15).fadeout(0.15)
            clips.append(final_clip)
            v.close()
        except Exception as e:
            st.warning(f"Errore nel processamento di {d.get('name')}: {e}")
            continue
        
        progress_bar.progress((i + 1) / len(data_list))
    
    if not clips:
        return None
   
    sizzle = mp.concatenate_videoclips(clips, method="compose")
    out = f"puglia_sizzle_{int(time.time())}.mp4"
    
    with st.spinner("Rendering video finale..."):
        sizzle.write_videofile(
            out,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset='ultrafast',
            threads=2,
            logger=None
        )
    return out

# --- SIDEBAR ---
with st.sidebar:
    st.header("📍 Bari/Puglia Config")
    cat = st.selectbox("Tipo Contenuto", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    
    files = st.file_uploader(
        "📤 Carica i video grezzi", 
        type=["mp4", "mov"], 
        accept_multiple_files=True,
        help="⚠️ Dimensione consigliata per video: fino a 400-500 MB. File più grandi possono causare problemi."
    )

# --- LOGICA PRINCIPALE ---
if files:
    # Avviso per file grandi
    for f in files:
        if f.size > 500 * 1024 * 1024:  # > 500 MB
            st.warning(f"⚠️ Il file **{f.name}** è molto grande ({f.size/1024/1024:.1f} MB). Potrebbero verificarsi errori di memoria.")

    if st.button("🔎 1. SCANSIONA HIGHLIGHTS ED ENERGIA", type="primary"):
        all_h = []
        temp_files = []   # per cleanup successivo
        
        with st.status("🛸 AI sta cercando i momenti più forti...", expanded=True) as stt:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            for f in files:
                stt.write(f"Scansione: **{f.name}**")
                
                # Salva file
                p = save_uploaded_file(f)
                temp_files.append(p)
                
                v_ai = genai.upload_file(path=p)
                
                # Attendi elaborazione
                while genai.get_file(v_ai.name).state.name == "PROCESSING":
                    time.sleep(4)
                    v_ai = genai.get_file(v_ai.name)
                
                time.sleep(8)  # Ridotto rispetto a 12
                
                prompt = f"""
                Sei un video editor professionista di Bari specializzato in contenuti virali Puglia.
                Analizza questo video di {cat} e trova il momento di picco energetico (drop, acuto, brindisi, emozione forte).
                Rispondi **SOLO** con JSON valido:
                {{"start": float, "reason": "breve spiegazione", "music": "3 canzoni trend Italia"}}
                """
                
                try:
                    r = model.generate_content(
                        [v_ai, prompt],
                        generation_config={"response_mime_type": "application/json"}
                    )
                    d = json.loads(r.text.strip())
                    d.update({'path': p, 'name': f.name})
                    all_h.append(d)
                except Exception as e:
                    st.error(f"Errore su {f.name}: {e}")
                    continue
           
            st.session_state['h_list'] = all_h
            st.session_state['temp_files'] = temp_files
            stt.update(label="✅ Analisi completata!", state="complete")

    # --- SECONDA PARTE ---
    if 'h_list' in st.session_state and st.session_state['h_list']:
        h_list = st.session_state['h_list']
        
        st.success(f"🔥 Isolati **{len(h_list)}** highlights forti!")
        
        with st.expander("👀 Anteprima Highlights trovati"):
            for h in h_list:
                st.write(f"✅ **{h['name']}** → {h.get('reason','N/D')} (al secondo **{h['start']}**)")

        st.info(f"🎵 **Musica suggerita:** {h_list[0].get('music', 'Non disponibile')}")

        if st.button("🎬 2. GENERA MONTAGGIO FINALE", type="primary"):
            with st.status("✂️ Creazione montaggio ritmico..."):
                final_video = create_sizzle(h_list, plat, ctype)
                
                if final_video and os.path.exists(final_video):
                    st.video(final_video)
                    with open(final_video, "rb") as fr:
                        st.download_button(
                            "📥 SCARICA VIDEO PRONTO",
                            fr,
                            file_name="puglia_sizzle_pro.mp4",
                            mime="video/mp4"
                        )
                else:
                    st.error("Errore nella generazione del video")

# --- PULIZIA ---
if st.button("🧹 Pulisci file temporanei"):
    if 'temp_files' in st.session_state:
        for path in st.session_state.temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass
        st.success("File temporanei eliminati")
        st.session_state.pop('temp_files', None)
