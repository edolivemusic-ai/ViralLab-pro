import streamlit as st
import tempfile
import os
import json
import time
import concurrent.futures
import numpy as np
from google import genai
from google.genai import types
from moviepy import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeAudioClip, CompositeVideoClip, TextClip,
)
from moviepy.video.fx import FadeIn, FadeOut
from moviepy.audio.fx import AudioFadeOut

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Highlights Video Detector",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Blocca font Material Icons che causa testo "keyboard_double" e "arrow_right" ── */
@font-face {
    font-family: 'Material Icons';
    src: local('Material Icons');
    unicode-range: U+E000-F8FF;
    font-display: block;
}
.material-icons,
.material-symbols-rounded,
[class*="material-icon"],
[class*="material-symbol"] {
    font-family: inherit !important;
    font-size: 0 !important;
    visibility: hidden !important;
    width: 0 !important;
    overflow: hidden !important;
}

/* ── Font ── */
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;600;800&display=swap');

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; }

/* ── Sfondo globale ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background-color: #080A0F !important;
    color: #E8E8E0 !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #080A0F !important; }
[data-testid="block-container"] { padding: 2rem 2.5rem 4rem !important; max-width: 100% !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0C0E15 !important;
    border-right: 1px solid #1A1F2E !important;
    min-width: 300px !important;
    max-width: 300px !important;
}
[data-testid="stSidebar"] * { font-family: 'DM Mono', monospace !important; }
[data-testid="stSidebarContent"] { padding: 1.2rem 1rem !important; }

/* ── Header: completamente rimosso ── */
header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
    overflow: hidden !important;
}
#MainMenu, footer { display: none !important; }

/* ── Pulsante apri/chiudi sidebar: fisso sul bordo sinistro, sempre visibile ── */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: fixed !important;
    left: 0 !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    z-index: 999999 !important;
    background: #00F0D4 !important;
    border-radius: 0 8px 8px 0 !important;
    width: 20px !important;
    height: 56px !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    border: none !important;
    box-shadow: 3px 0 12px rgba(0,240,212,0.4) !important;
    padding: 0 !important;
}
[data-testid="collapsedControl"] * {
    color: #080A0F !important;
    font-size: 14px !important;
    font-family: sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #080A0F; }
::-webkit-scrollbar-thumb { background: #00F0D4; border-radius: 2px; }

/* ── Hero ── */
.hero-block { padding: 2rem 0 2rem; }
.hero-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.25em;
    color: #00F0D4; text-transform: uppercase; margin-bottom: 0.5rem;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(4rem, 9vw, 8rem);
    line-height: 0.9; color: #FFFFFF; letter-spacing: 0.01em;
}
.hero-title span { color: transparent; -webkit-text-stroke: 2px #00F0D4; }
.hero-sub {
    font-size: 0.88rem; font-weight: 300;
    color: #5A6070; margin-top: 0.8rem; letter-spacing: 0.03em;
}
.hero-line {
    height: 1px;
    background: linear-gradient(90deg, #00F0D4 0%, #FF2D5533 60%, transparent 100%);
    margin: 1.5rem 0 0;
}

/* ── Section label ── */
.section-label {
    font-family: 'DM Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.3em; color: #00F0D4; text-transform: uppercase;
    margin-bottom: 0.8rem; margin-top: 2rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.section-label::after { content: ''; flex: 1; height: 1px; background: #1A1F2E; }

/* ── Sidebar section label ── */
.sidebar-section {
    font-family: 'DM Mono', monospace; font-size: 0.58rem;
    letter-spacing: 0.25em; color: #00F0D4; text-transform: uppercase;
    margin-bottom: 0.5rem; margin-top: 1.2rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.sidebar-section::after { content: ''; flex: 1; height: 1px; background: #1A1F2E; }

/* ── Highlight card ── */
.highlight-card {
    background: #0E1118; border: 1px solid #1A1F2E;
    border-left: 3px solid #00F0D4; border-radius: 6px;
    padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
}
.hc-name { font-family: 'DM Mono', monospace; font-size: 0.75rem; color: #00F0D4; margin-bottom: 0.25rem; }
.hc-reason { font-size: 0.82rem; color: #8891A4; margin-bottom: 0.2rem; }
.hc-meta { font-family: 'DM Mono', monospace; font-size: 0.68rem; color: #3D4455; }
.hc-meta span { color: #FF2D55; }
.hc-insight {
    font-family: 'DM Mono', monospace; font-size: 0.7rem;
    color: #FF9500; margin-top: 0.5rem;
    border-left: 2px solid #FF950055; padding-left: 0.5rem;
}

/* ── Status box ── */
.platform-warning {
    background: #150A0E; border: 1px solid #FF2D5555;
    border-left: 3px solid #FF2D55; border-radius: 6px;
    padding: 0.8rem 1rem; font-family: 'DM Mono', monospace;
    font-size: 0.75rem; color: #FF2D55; margin: 0.8rem 0;
}
.platform-ok {
    background: #080F0E; border: 1px solid #00F0D433;
    border-left: 3px solid #00F0D4; border-radius: 6px;
    padding: 0.8rem 1rem; font-family: 'DM Mono', monospace;
    font-size: 0.75rem; color: #00F0D4; margin: 0.8rem 0;
}

/* ── Bottoni Streamlit ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #00F0D4 !important;
    color: #00F0D4 !important; border-radius: 3px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.2s !important; width: 100% !important;
}
.stButton > button:hover { background: #00F0D4 !important; color: #080A0F !important; }
button[kind="primary"] {
    background: #00F0D4 !important; color: #080A0F !important;
    border-color: #00F0D4 !important; font-weight: 700 !important;
}
button[kind="primary"]:hover { background: #00D4BB !important; }

/* ── Input / Select ── */
.stSelectbox [data-baseweb="select"] > div,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background: #0C0E15 !important; border-color: #1A1F2E !important;
    color: #E8E8E0 !important; font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important; border-radius: 4px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
    background: #0C0E15 !important;
    border: 1px dashed #1A1F2E !important;
    border-radius: 6px !important;
    padding: 0.8rem !important;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.65rem !important;
    color: #3D4455 !important;
}
/* Nasconde SOLO le icone Material nel file uploader, non il testo */
[data-testid="stFileUploaderDropzone"] .material-icons,
[data-testid="stFileUploaderDropzone"] .material-symbols-rounded {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: #0C0E15 !important;
    border: 1px solid #1A1F2E !important;
    color: #5A6070 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.65rem !important;
    border-radius: 3px !important;
}

/* ── File caricati (badge nomi file) ── */
[data-testid="stFileUploaderFile"] {
    background: #0E1118 !important;
    border: 1px solid #1A1F2E !important;
    border-radius: 4px !important;
    padding: 0.4rem 0.6rem !important;
    margin-bottom: 0.3rem !important;
}
[data-testid="stFileUploaderFile"] span,
[data-testid="stFileUploaderFileName"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    color: #00F0D4 !important;
}
[data-testid="stFileUploaderFileData"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.62rem !important;
    color: #3D4455 !important;
}

/* ── Labels ── */
.stSelectbox label, .stRadio label, .stSlider label,
.stTextInput label, .stTextArea label, .stFileUploader label,
.stToggle label, .stNumberInput label, .stCheckbox label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.65rem !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important; color: #5A6070 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] summary {
    background: #0C0E15 !important;
    border: 1px solid #1A1F2E !important;
    border-radius: 4px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    color: #8891A4 !important;
    list-style: none !important;
    padding: 0.5rem 0.8rem !important;
}
[data-testid="stExpander"] summary svg { color: #3D4455 !important; }
/* Nasconde testo "arrow_right" che trapela dall expander */
[data-testid="stExpander"] summary .material-icons,
[data-testid="stExpander"] summary .material-symbols-rounded {
    display: none !important;
}
[data-testid="stExpanderDetails"] {
    background: #0C0E15 !important;
    border: 1px solid #1A1F2E !important;
    border-top: none !important;
    padding: 0.8rem !important;
}

/* ── Radio orizzontale ── */
.stRadio [data-testid="stWidgetLabel"] { display: none !important; }
.stRadio > div[role="radiogroup"] { flex-direction: row !important; gap: 0.5rem !important; }

/* ── Status ── */
[data-testid="stStatus"] {
    background: #0C0E15 !important; border-color: #1A1F2E !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important;
}

/* ── Slider ── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: #00F0D4 !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] > div {
    background: #1A1F2E !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] > div > div {
    background: #00F0D4 !important;
}

/* ── Divider ── */
hr { border-color: #1A1F2E !important; margin: 1rem 0 !important; }

/* ── Sidebar logo ── */
.sidebar-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem; letter-spacing: 0.08em; color: #FFFFFF; margin-bottom: 0.1rem;
}
.sidebar-logo span { color: #00F0D4; }
.sidebar-version {
    font-family: 'DM Mono', monospace; font-size: 0.55rem;
    letter-spacing: 0.2em; color: #2A3040; text-transform: uppercase;
    margin-bottom: 0.5rem;
}

/* ── History ── */
.history-entry {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; color: #3D4455;
    border-left: 2px solid #1A1F2E; padding: 0.35rem 0.7rem; margin-bottom: 0.4rem;
}

/* ── Pulse animation ── */
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────
MAX_CLIPS = 10

PLATFORM_LIMITS = {
    "Instagram": {"Reels": 90,  "Storie": 60,  "Post": 60},
    "TikTok":    {"Reels": 180, "Storie": 60,  "Post": 180},
    "Facebook":  {"Reels": 60,  "Storie": 20,  "Post": 240},
}

FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)},
}

DEFAULT_PROMPT = (
    "Sei un video editor e social media strategist professionista di Bari, "
    "specializzato in contenuti virali per il mercato Puglia e Italia. "
    "Puoi analizzare sia video PROPRI che video di COMPETITOR per estrarne insight strategici. "
    "Analizza questo video di {cat} e: "
    "1) Trova il momento di picco energetico (drop, acuto, brindisi, emozione forte, interazione pubblico). "
    "2) Valuta la qualita della ripresa e del montaggio. "
    "3) Identifica eventuali strategie social vincenti (ritmo, hashtag visibili, call-to-action, testo overlay). "
    "Rispondi SOLO con JSON valido, senza markdown, senza backtick: "
    '{"start": float, "reason": "momento chiave e perche funziona", '
    '"music": "3 canzoni trend Italia adatte", '
    '"competitor_insight": "cosa fa bene questo video che puoi replicare o migliorare"}'
)

# ─────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY.")
    st.stop()

@st.cache_resource
def get_client(key: str):
    return genai.Client(api_key=key)

client = get_client(api_key)

# ─────────────────────────────────────────
# FUNZIONI
# ─────────────────────────────────────────

def save_to_disk(file_dict: dict) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(file_dict["bytes"])
        return t.name

def cleanup(paths: list):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.unlink(p)
        except Exception:
            pass

def get_audio_peak(video_path: str, start_hint: float = 0.0) -> float:
    """
    Rimossa analisi audio locale per risparmiare RAM su Render free tier.
    Gemini 2.5 Flash è già preciso nel trovare il momento di picco.
    """
    return start_hint

def scan_video(file_dict: dict, prompt_tmpl: str, cat: str) -> dict:
    p = save_to_disk(file_dict)
    ref = None
    try:
        with open(p, "rb") as fh:
            ref = client.files.upload(
                file=fh,
                config=types.UploadFileConfig(
                    display_name=file_dict["name"],
                    mime_type="video/mp4",
                )
            )
        for _ in range(30):
            info = client.files.get(name=ref.name)
            if info.state.name == "ACTIVE": break
            if info.state.name == "FAILED": raise RuntimeError("Upload Gemini fallito")
            time.sleep(5)
        time.sleep(2)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_uri(file_uri=ref.uri, mime_type="video/mp4"),
                prompt_tmpl.replace("{cat}", cat),
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = response.text.strip().replace("```json", "").replace("```", "")
        d = json.loads(raw)
        ai_start = float(d.get("start", 0))
        d["start_ai"] = ai_start
        d["start"]    = get_audio_peak(p, start_hint=ai_start)
        d["path"]     = p
        d["name"]     = file_dict["name"]
        d["include"]  = True
        return d
    except Exception as err:
        cleanup([p])
        return {"error": str(err), "name": file_dict["name"], "path": None}
    finally:
        if ref:
            try: client.files.delete(name=ref.name)
            except Exception: pass

def render_mashup(
    highlights: list, plat: str, ctype: str, clip_dur: float,
    add_wm: bool, wm_text: str, audio_path: str | None
) -> str | None:
    tw, th = FMT[plat][ctype]
    target = float(PLATFORM_LIMITS[plat][ctype])
    n = len(highlights)
    if n == 0: return None

    base_total = n * clip_dur
    repeats    = max(1, int(np.ceil(target / base_total)))
    opt_dur    = target / (n * repeats)

    st.info(f"🎬 Target **{target:.0f}s** · {n} highlight × {repeats} loop · **{opt_dur:.1f}s** per clip")

    clips = []
    bar = st.progress(0)
    accumulated = 0.0
    loop_idx = 0

    while accumulated < target and loop_idx <= 20:
        for h in highlights:
            if accumulated >= target: break
            dur = min(opt_dur, target - accumulated)
            if dur < 0.3: break
            try:
                v = VideoFileClip(h["path"])
                s = float(h.get("start", 0))
                e = min(s + dur, v.duration)
                if e <= s: v.close(); continue

                # Esporta il singolo clip in un file temporaneo
                # → evita di tenere tutti i frame in RAM contemporaneamente
                clip_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                clip_raw = v.subclipped(s, e).resized(height=th)
                if clip_raw.w > tw:
                    clip_raw = clip_raw.cropped(x_center=clip_raw.w / 2, width=tw)
                clip_raw = clip_raw.with_effects([FadeIn(0.15), FadeOut(0.15)])
                clip_raw.write_videofile(clip_tmp, codec="libx264", audio_codec="aac",
                                         fps=24, preset="ultrafast", threads=1, logger=None)
                clip_raw.close()
                v.close()

                # Ricarica solo il riferimento al file (pochissima RAM)
                clip_ref = VideoFileClip(clip_tmp)
                clips.append((clip_ref, clip_tmp))
                accumulated += clip_ref.duration
                bar.progress(min(accumulated / target, 1.0))
            except Exception as err:
                st.warning(f"Clip {h.get('name')}: {err}")
        loop_idx += 1

    if not clips: return None

    clip_refs = [c for c, _ in clips]
    clip_tmps = [t for _, t in clips]

    sizzle = concatenate_videoclips(clip_refs, method="compose")

    if audio_path and os.path.exists(audio_path):
        try:
            bg = (AudioFileClip(audio_path)
                  .subclipped(0, sizzle.duration)
                  .with_effects([AudioFadeOut(1.5)])
                  .with_volume_scaled(0.85))
            fa = (CompositeAudioClip([bg, sizzle.audio.with_volume_scaled(0.3)])
                  if sizzle.audio else bg)
            sizzle = sizzle.with_audio(fa)
        except Exception as err:
            st.warning(f"Audio: {err}")

    out = f"mashup_{int(time.time())}.mp4"
    sizzle.write_videofile(out, codec="libx264", audio_codec="aac",
                           fps=24, preset="ultrafast", threads=2, logger=None)

    # Chiudi e pulisci tutto
    for c in clip_refs:
        try: c.close()
        except Exception: pass
    sizzle.close()
    for t in clip_tmps:
        try: os.unlink(t)
        except Exception: pass

    return out

# ─────────────────────────────────────────
# SIDEBAR — tutto qui dentro
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="sidebar-version">v4.0 · Gemini 2.5 Flash · Own &amp; Competitor</div>
    """, unsafe_allow_html=True)

    # ── Configurazione ──
    st.markdown('<div class="sidebar-section">// contenuto</div>', unsafe_allow_html=True)
    cat_w = st.selectbox("Tipo",
        ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"],
        label_visibility="visible")

    st.markdown('<div class="sidebar-section">// piattaforma</div>', unsafe_allow_html=True)
    plat_w  = st.selectbox("Social", ["Instagram", "TikTok", "Facebook"],
                           label_visibility="visible")
    ctype_w = st.radio("Formato", ["Reels", "Storie", "Post"],
                       horizontal=True, label_visibility="collapsed")
    limit_sec = PLATFORM_LIMITS[plat_w][ctype_w]
    st.caption(f"max {limit_sec}s · {plat_w} {ctype_w}")

    # ── Upload video ──
    st.markdown('<div class="sidebar-section">// video</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Carica video",
        type=["mp4", "mov"], accept_multiple_files=True,
        label_visibility="collapsed")

    # Salva file come bytes in session_state (sopravvivono al re-render)
    if uploaded:
        st.session_state["_files"] = [
            {"name": f.name, "size": f.size, "bytes": f.getvalue()}
            for f in uploaded
        ]
        st.session_state["_cat"]   = cat_w
        st.session_state["_plat"]  = plat_w
        st.session_state["_ctype"] = ctype_w

    # ── Opzioni avanzate ──
    st.markdown('<div class="sidebar-section">// opzioni</div>', unsafe_allow_html=True)
    clip_dur = st.slider("Durata clip (s)", 1.0, 6.0, 2.8, 0.1,
                         label_visibility="visible")
    add_wm = st.toggle("Watermark", value=False)
    wm_text = ""
    if add_wm:
        wm_text = st.text_input("Testo watermark", value="#HighlightsVD",
                                label_visibility="collapsed")

    st.markdown('<div class="sidebar-section">// audio</div>', unsafe_allow_html=True)
    audio_up = st.file_uploader("Colonna sonora",
        type=["mp3", "wav", "aac", "m4a"],
        label_visibility="collapsed")

    with st.expander("Prompt AI"):
        custom_prompt = st.text_area("Prompt", value=DEFAULT_PROMPT, height=140,
                                     label_visibility="collapsed")
        st.session_state["_prompt"] = custom_prompt

# ─────────────────────────────────────────
# LEGGI SESSION STATE (fonte unica di verità)
# ─────────────────────────────────────────
file_data = st.session_state.get("_files", [])
cat       = st.session_state.get("_cat",   cat_w)
plat      = st.session_state.get("_plat",  plat_w)
ctype     = st.session_state.get("_ctype", ctype_w)
limit_sec = PLATFORM_LIMITS[plat][ctype]
prompt    = st.session_state.get("_prompt", DEFAULT_PROMPT)

# ─────────────────────────────────────────
# PAGINA PRINCIPALE
# ─────────────────────────────────────────

# Hero
st.markdown("""
<div class="hero-block">
    <div class="hero-eyebrow">⚡ AI-Powered · Real-time Analysis</div>
    <div class="hero-title">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="hero-sub">Gemini 2.5 Flash · Analisi propri video &amp; competitor · Mashup automatico</div>
    <div class="hero-line"></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# STEP 1 — Scansione (solo se ci sono file)
# ─────────────────────────────────────────
if file_data:
    MAX_FILE_MB = 200
    file_data = [f for f in file_data if f["size"] <= MAX_FILE_MB * 1024 * 1024]
    st.session_state["_files"] = file_data  # aggiorna dopo filtro

    for f in file_data:
        mb = f["size"] / 1024 / 1024
        color = "#FF2D55" if mb > 150 else "#00F0D4"
        st.markdown(
            f'<div class="platform-ok" style="border-left-color:{color}">📹 {f["name"]} · {mb:.0f} MB</div>',
            unsafe_allow_html=True)

    if len(file_data) > MAX_CLIPS:
        st.markdown(
            f'<div class="platform-warning">↳ verranno processati solo i primi {MAX_CLIPS} file</div>',
            unsafe_allow_html=True)

    st.markdown('<div class="section-label">// step 01 — analisi</div>', unsafe_allow_html=True)
    col_btn, col_inf = st.columns([3, 1])
    with col_btn:
        scan_btn = st.button("⚡ SCANSIONA HIGHLIGHTS", type="primary")
    with col_inf:
        st.markdown(
            f'<div style="font-family:\'DM Mono\',monospace;font-size:0.6rem;'
            f'color:#3D4455;padding-top:0.75rem;">'
            f'{len(file_data)} FILE · {cat.upper()}</div>',
            unsafe_allow_html=True)

    if scan_btn:
        total_files = min(len(file_data), MAX_CLIPS)
        progress_bar = st.progress(0, text="Preparazione analisi...")
        completed = [0]  # lista mutabile per aggiornamento da thread

        with st.status("Analisi in corso...", expanded=True) as status:
            all_h, paths, errors = [], [], []

            def scan_with_progress(f):
                result = scan_video(f, prompt, cat)
                completed[0] += 1
                pct = completed[0] / total_files
                progress_bar.progress(
                    pct,
                    text=f"Scansione {completed[0]}/{total_files} · {f['name'][:30]}..."
                )
                return result

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
                fut_map = {
                    ex.submit(scan_with_progress, f): f
                    for f in file_data[:MAX_CLIPS]
                }
                for fut in concurrent.futures.as_completed(fut_map):
                    fref = fut_map[fut]
                    try:
                        res = fut.result()
                        if "error" in res:
                            errors.append(res)
                            st.markdown(f'`✗ {res["name"]}` — {res["error"]}')
                        else:
                            all_h.append(res)
                            if res["path"]: paths.append(res["path"])
                            st.markdown(
                                f'`✓ {res["name"]}` '
                                f'— AI `{res.get("start_ai",0):.1f}s` '
                                f'→ peak `{res["start"]:.1f}s`')
                    except Exception as err:
                        errors.append({"name": fref["name"], "error": str(err)})

            st.session_state["_highlights"]  = all_h
            st.session_state["_temp_paths"]  = paths
            st.session_state["_scan_errors"] = errors
            progress_bar.progress(1.0, text=f"✓ Completato — {len(all_h)} highlights trovati")
            status.update(label=f"✓ {len(all_h)} highlights trovati", state="complete")

# ─────────────────────────────────────────
# STEP 2 — Editor (appare se ci sono risultati)
# ─────────────────────────────────────────
if st.session_state.get("_highlights"):
    h_list = st.session_state["_highlights"]

    # Retry errori
    if st.session_state.get("_scan_errors"):
        for err in st.session_state["_scan_errors"]:
            c1, c2 = st.columns([5, 1])
            c1.markdown(
                f'<div class="platform-warning">✗ {err["name"]} — {err.get("error","")}</div>',
                unsafe_allow_html=True)
            if c2.button("↺", key=f"retry_{err['name']}"):
                match = [f for f in file_data if f["name"] == err["name"]]
                if match:
                    with st.spinner("Retry..."):
                        res = scan_video(match[0], prompt, cat)
                        if "error" not in res:
                            st.session_state["_highlights"].append(res)
                            if res["path"]:
                                st.session_state["_temp_paths"].append(res["path"])
                            st.session_state["_scan_errors"] = [
                                e for e in st.session_state["_scan_errors"]
                                if e["name"] != err["name"]
                            ]
                            st.rerun()
                        else:
                            st.error(res["error"])

    st.markdown('<div class="section-label">// step 02 — highlights</div>', unsafe_allow_html=True)

    for h in h_list:
        insight = h.get('competitor_insight', '')
        insight_html = (
            f'<div class="hc-insight">💡 {insight}</div>'
            if insight else ""
        )
        st.markdown(f"""
        <div class="highlight-card">
            <div class="hc-name">▸ {h['name']}</div>
            <div class="hc-reason">{h.get('reason','N/D')}</div>
            <div class="hc-meta">
                AI: <span>{h.get('start_ai',0):.1f}s</span> &nbsp;·&nbsp;
                AUDIO PEAK: <span>{h.get('start',0):.1f}s</span> &nbsp;·&nbsp;
                MUSICA: {h.get('music','—')}
            </div>
            {insight_html}
        </div>""", unsafe_allow_html=True)

    with st.expander("Modifica Parametri Clip"):
        updated = []
        for i, h in enumerate(h_list):
            c = st.columns([0.5, 1, 1, 2])
            inc   = c[0].checkbox("ON", value=h.get("include", True), key=f"inc_{i}")
            c[0].caption(h["name"][:16])
            ns    = c[1].number_input("Inizio (s)", 0.0, value=float(h.get("start",0)), step=0.5, key=f"st_{i}")
            nd    = c[2].number_input("Durata (s)", 0.5, 10.0, float(clip_dur), 0.1, key=f"du_{i}")
            c[3].caption(f"💡 {h.get('reason','')[:55]}")
            hc = dict(h)
            hc.update({"include": inc, "start": ns, "clip_duration_override": nd})
            updated.append(hc)
        st.session_state["_highlights"] = updated

    active   = [h for h in st.session_state["_highlights"] if h.get("include", True)]
    n_active = len(active)
    base_tot = n_active * clip_dur
    reps     = max(1, int(np.ceil(limit_sec / base_tot))) if base_tot > 0 else 1
    opt      = limit_sec / max(1, n_active * reps)

    st.markdown(
        f'<div class="platform-ok">'
        f'🎬 MASHUP TARGET: <b>{limit_sec:.0f}s</b> · '
        f'{n_active} highlight × {reps} loop · '
        f'<b>{opt:.1f}s</b> per clip · {plat} {ctype}'
        f'</div>', unsafe_allow_html=True)

    if h_list:
        st.markdown(
            f'<div class="platform-ok">🎵 {h_list[0].get("music","N/D")}</div>',
            unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # STEP 3 — Render
    # ─────────────────────────────────────────
    st.markdown('<div class="section-label">// step 03 — genera mashup</div>', unsafe_allow_html=True)
    cr, ci = st.columns([3, 1])
    with cr:
        render_btn = st.button("▶ GENERA MASHUP FINALE", type="primary")
    with ci:
        st.markdown(
            f'<div style="font-family:\'DM Mono\',monospace;font-size:0.6rem;'
            f'color:#3D4455;padding-top:0.75rem;">'
            f'{n_active} CLIP · {plat.upper()}</div>',
            unsafe_allow_html=True)

    if render_btn:
        data = [h for h in st.session_state["_highlights"] if h.get("include", True)]

        # Salva audio
        audio_path = st.session_state.get("_audio_path")
        if audio_up and not audio_path:
            ext = os.path.splitext(audio_up.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as af:
                af.write(audio_up.getvalue())
                audio_path = af.name
                st.session_state["_audio_path"] = audio_path

        with st.status("Rendering...", expanded=False):
            final = render_mashup(data, plat, ctype, clip_dur, add_wm, wm_text, audio_path)

        if final and os.path.exists(final):
            st.markdown('<div class="section-label">// output</div>', unsafe_allow_html=True)
            st.video(final)

            if "_history" not in st.session_state:
                st.session_state["_history"] = []
            st.session_state["_history"].append({
                "time": time.strftime("%H:%M:%S"),
                "platform": f"{plat} {ctype}",
                "clips": len(data),
                "duration": f"{limit_sec:.0f}s",
            })

            with open(final, "rb") as fr:
                st.download_button("↓ SCARICA MASHUP", fr,
                                   file_name="mashup.mp4", mime="video/mp4")
            try: os.unlink(final)
            except Exception: pass
        else:
            st.error("Errore nella generazione del video.")

# ─────────────────────────────────────────
# STORICO
# ─────────────────────────────────────────
if st.session_state.get("_history"):
    st.markdown('<div class="section-label">// sessione</div>', unsafe_allow_html=True)
    for e in reversed(st.session_state["_history"]):
        st.markdown(
            f'<div class="history-entry">'
            f'{e["time"]} · {e["platform"]} · {e["clips"]} clip · {e["duration"]}'
            f'</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# PULIZIA
# ─────────────────────────────────────────
if st.session_state.get("_temp_paths"):
    st.markdown('<div style="margin-top:3rem;"></div>', unsafe_allow_html=True)
    if st.button("✕ PULISCI FILE TEMPORANEI"):
        cleanup(st.session_state.get("_temp_paths", []))
        if "_audio_path" in st.session_state:
            cleanup([st.session_state.pop("_audio_path")])
        for k in ["_temp_paths", "_highlights", "_scan_errors", "_files"]:
            st.session_state.pop(k, None)
        st.success("✓ Pulizia completata.")
        st.rerun()
