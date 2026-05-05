import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile, os, json, time
from google.api_core import exceptions

st.set_page_config(page_title="Music Viral Lab Pro", layout="wide")
st.markdown("<style>.main{background-color:#0f1116;color:#f0f2f6;}.stButton>button{background:linear-gradient(90deg,#FF0050 0%,#00f2ea 100%);color:white;border-radius:10px;width:100%;}</style>", unsafe_allow_html=True)
st.title("🎙️ Music Viral Lab")

api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Configura GEMINI_API_KEY nei Secrets.")
    st.stop()
genai.configure(api_key=api_key)

FMT = {
    "Instagram": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1350)},
    "TikTok": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1920)},
    "Facebook": {"Reels": (1080, 1920), "Storie": (1080, 1920), "Post": (1080, 1080)}
}

def auto_edit(path, plat, ctype, start, end):
    try:
        with mp.VideoFileClip(path) as video:
            tw, th = FMT[plat][ctype]
            s, e = max(0, float(start)), min(float(end), video.duration)
            if e <= s: e = s + 10
            clip = video.subclip(s, e).resize(height=th)
            final = clip.crop(x_center=clip.w/2, width=tw) if clip.w > tw else clip
            out = f"fin_{int(time.time())}.mp4"
            final.write_videofile(out, codec="libx264", audio_codec="aac", fps=24, logger=None, preset='ultrafast', threads=1)
            return out
    except Exception as ex:
        st.error(f"Errore montaggio: {ex}")
        return None

with st.sidebar:
    cat = st.selectbox("Categoria", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])
    files = st.file_uploader("Carica Video", type=["mp4", "mov"], accept_multiple_files=True)

res_c = st.container()

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
                time.sleep(12)
                model = genai.GenerativeModel(model_name='gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
                prompt = f"Expert editor for {cat}. Find viral clip (7-12s). JSON: 'start' (float), 'end' (float), 'caption' (str)"
                data = None
                for att in range(4):
                    try:
                        resp = model.generate_content([v_ai, prompt])
                        data = json.loads(resp.text)
                        break
                    except:
                        time.sleep(10)
                if not data: continue
                stt.update(label="Montaggio fisico...")
                out = auto_edit(p, plat, ctype, data['start'], data['end'])
                if out:
                    with res_c:
                        st.success(f"✅ {f.name} PRONTO")
                        c1, c2 = st.columns(2)
                        with c1: st.video(out)
                        with c2:
                            st.code(data['caption'])
                            with open(out, "rb") as o_f:
                                st.download_button(f"Scarica {f.name}", o_f, file_name=f"viral_{f.name}")
                stt.update(label="Fatto!", state="complete")
        except Exception as err: st.error(f"Errore: {err}")
        finally:
            if os.path.exists(p): os.remove(p)
            if v_ai:
                try: genai.delete_file(v_ai.name)
                except: pass
