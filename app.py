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
    initial_sidebar_state="auto",
)

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;600;800&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #080A0F !important; color: #E8E8E0 !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #080A0F !important; }
[data-testid="block-container"] { padding: 2rem 2.5rem 4rem !important; }
[data-testid="stSidebar"] { background: #0C0E15 !important; border-right: 1px solid #1A1F2E !important; }
[data-testid="stSidebar"] * { font-family: 'DM Mono', monospace !important; }
[data-testid="stSidebarContent"] { padding: 1.5rem 1rem !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #080A0F; }
::-webkit-scrollbar-thumb { background: #00F0D4; border-radius: 2px; }
.hero-block { padding: 3rem 0 2.5rem; }
.hero-eyebrow { font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.25em; color: #00F0D4; text-transform: uppercase; margin-bottom: 0.6rem; }
.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: clamp(3.5rem, 8vw, 7rem); line-height: 0.92; color: #FFFFFF; }
.hero-title span { color: transparent; -webkit-text-stroke: 1.5px #00F0D4; }
.hero-sub { font-size: 0.9rem; font-weight: 300; color: #5A6070; margin-top: 1rem; }
.hero-line { height: 1px; background: linear-gradient(90deg, #00F0D4 0%, #FF2D5533 60%, transparent 100%); margin: 2rem 0 0; }
.section-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 0.3em; color: #00F0D4; text-transform: uppercase; margin-bottom: 1rem; margin-top: 2.5rem; display: flex; align-items: center; gap: 0.6rem; }
.section-label::after { content: ''; flex: 1; height: 1px; background: #1A1F2E; }
.highlight-card { background: #0E1118; border: 1px solid #1A1F2E; border-left: 3px solid #00F0D4; border-radius: 6px; padding: 1rem 1.2rem; margin-bottom: 0.75rem; }
.highlight-card .hc-name { font-family: 'DM Mono', monospace; font-size: 0.78rem; color: #00F0D4; margin-bottom: 0.3rem; }
.highlight-card .hc-reason { font-size: 0.85rem; color: #8891A4; margin-bottom: 0.25rem; }
.highlight-card .hc-meta { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: #3D4455; }
.highlight-card .hc-meta span { color: #FF2D55; }
.platform-warning { background: #150A0E; border: 1px solid #FF2D5555; border-left: 3px solid #FF2D55; border-radius: 6px; padding: 0.9rem 1.2rem; font-family: 'DM Mono', monospace; font-size: 0.78rem; color: #FF2D55; margin: 1rem 0; }
.platform-ok { background: #080F0E; border: 1px solid #00F0D433; border-left: 3px solid #00F0D4; border-radius: 6px; padding: 0.9rem 1.2rem; font-family: 'DM Mono', monospace; font-size: 0.78rem; color: #00F0D4; margin: 1rem 0; }
.stButton > button { background: transparent !important; border: 1px solid #00F0D4 !important; color: #00F0D4 !important; border-radius: 3px !important; font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; padding: 0.65rem 1.5rem !important; transition: all 0.2s !important; width: 100% !important; }
.stButton > button:hover { background: #00F0D4 !important; color: #080A0F !important; }
button[kind="primary"] { background: #00F0D4 !important; color: #080A0F !important; border-color: #00F0D4 !important; font-weight: 600 !important; }
.stSelectbox > div > div, .stRadio > div, .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stFileUploader > div { background: #0C0E15 !important; border-color: #1A1F2E !important; color: #E8E8E0 !important; font-family: 'DM Mono', monospace !important; font-size: 0.8rem !important; border-radius: 4px !important; }
.stSelectbox label, .stRadio label, .stSlider label, .stTextInput label, .stTextArea label, .stFileUploader label, .stToggle label, .stNumberInput label { font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; color: #5A6070 !important; }
[data-testid="stStatus"] { background: #0C0E15 !important; border-color: #1A1F2E !important; font-family: 'DM Mono', monospace !important; font-size: 0.78rem !important; }
.sidebar-logo { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 0.08em; color: #FFFFFF; margin-bottom: 0.2rem; }
.sidebar-logo span { color: #00F0D4; }
.sidebar-version { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #2A3040; text-transform: uppercase; margin-bottom: 1.5rem; }
.history-entry { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #3D4455; border-left: 2px solid #1A1F2E; padding: 0.4rem 0.75rem; margin-bottom: 0.5rem; }
.stNumberInput input { background: #0C0E15 !important; border-color: #1A1F2E !important; color: #E8E8E0 !important; font-family: 'DM Mono', monospace !important; }
#MainMenu, footer { visibility: hidden !important; }
header { visibility: visible !important; }
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; color: #00F0D4 !important; }
@keyframes fadeSlideUp { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.dot-live { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #00F0D4; animation: pulse 1.6s ease infinite; margin-right: 6px; vertical-align: middle; }
hr { border-color: #1A1F2E !important; margin: 1.5rem 0 !important; }
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
    "Sei un video editor professionista di Bari specializzato in contenuti virali Puglia. "
    "Analizza questo video di {cat} e trova il momento di picco energetico "
    "(drop, acuto, brindisi, emozione forte). "
    "Rispondi SOLO con JSON valido, senza markdown, senza backtick: "
    '{"start": float, "reason": "breve spiegazione", "music": "3 canzoni trend Italia"}'
)

# ─────────────────────────────────────────
# API KEY & CLIENT
# ─────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY. Aggiungila come variabile d'ambiente su Render.")
    st.stop()

@st.cache_resource
def get_genai_client(key: str):
    return genai.Client(api_key=key)

client = get_genai_client(api_key)

# ─────────────────────────────────────────
# FUNZIONI
# ─────────────────────────────────────────

def save_file_to_disk(file_dict: dict) -> str:
    """Salva bytes su disco e ritorna il path temporaneo."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(file_dict["bytes"])
        return t.name

def cleanup_files(paths: list):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass

def get_audio_peak(video_path: str, start_hint: float = 0.0) -> float:
    """Trova il picco audio RMS nell'intorno ±10s del suggerimento AI."""
    try:
        v = VideoFileClip(video_path)
        if v.audio is None:
            v.close()
            return start_hint
        duration = v.duration
        step = 0.5
        timestamps = np.arange(0, max(0, duration - step), step)
        if len(timestamps) == 0:
            v.close()
            return start_hint
        rms_values = []
        for t in timestamps:
            chunk = v.audio.subclipped(t, min(t + step, duration))
            samples = chunk.to_soundarray(fps=22050)
            rms = float(np.sqrt(np.mean(samples ** 2)))
            rms_values.append(rms)
        v.close()
        idx_start = int(max(0, start_hint - 10) / step)
        idx_end   = int(min(duration, start_hint + 10) / step)
        window = rms_values[idx_start:idx_end]
        peak_idx = (idx_start + int(np.argmax(window))) if window else int(np.argmax(rms_values))
        return float(timestamps[min(peak_idx, len(timestamps) - 1)])
    except Exception:
        return start_hint

def scan_single_video(file_dict: dict, prompt_template: str, cat: str) -> dict:
    """
    Carica il video su Gemini, ottiene il momento di picco energetico,
    lo affina con analisi audio locale.
    Ritorna un dict con i dati dell'highlight oppure {'error': ..., 'name': ...}.
    """
    p = save_file_to_disk(file_dict)
    uploaded_ref = None
    try:
        with open(p, "rb") as fh:
            uploaded_ref = client.files.upload(
                file=fh,
                config=types.UploadFileConfig(
                    display_name=file_dict["name"],
                    mime_type="video/mp4",
                )
            )
        # Attendi che Gemini processi il file
        for _ in range(30):
            info = client.files.get(name=uploaded_ref.name)
            if info.state.name == "ACTIVE":
                break
            if info.state.name == "FAILED":
                raise RuntimeError("Gemini: elaborazione file fallita")
            time.sleep(5)
        time.sleep(2)

        prompt = prompt_template.replace("{cat}", cat)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                types.Part.from_uri(file_uri=uploaded_ref.uri, mime_type="video/mp4"),
                prompt,
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = response.text.strip().replace("```json", "").replace("```", "")
        d = json.loads(raw)

        # Affina con analisi audio locale
        ai_start = float(d.get("start", 0))
        audio_peak = get_audio_peak(p, start_hint=ai_start)
        d["start_ai"]  = ai_start
        d["start"]     = audio_peak
        d["path"]      = p
        d["name"]      = file_dict["name"]
        d["include"]   = True
        return d

    except Exception as err:
        cleanup_files([p])
        return {"error": str(err), "name": file_dict["name"], "path": None}
    finally:
        if uploaded_ref:
            try:
                client.files.delete(name=uploaded_ref.name)
            except Exception:
                pass

def render_sizzle(
    highlights: list,
    plat: str,
    ctype: str,
    clip_duration: float,
    add_watermark: bool,
    watermark_text: str,
    audio_path: str | None,
) -> str | None:
    """
    Genera un mashup che riempie la durata MASSIMA per piattaforma/formato.
    Riutilizza gli highlight in loop finché non si raggiunge il target.
    """
    tw, th = FMT[plat][ctype]
    target_sec = float(PLATFORM_LIMITS[plat][ctype])

    # Calcola durata ottimale per clip
    n = len(highlights)
    base_total = n * clip_duration
    repeats = max(1, int(np.ceil(target_sec / base_total)))
    optimal_dur = target_sec / (n * repeats)

    st.info(
        f"🎬 Target: **{target_sec:.0f}s** · "
        f"{n} highlight × {repeats} loop · "
        f"**{optimal_dur:.1f}s** per clip"
    )

    clips = []
    progress_bar = st.progress(0)
    accumulated = 0.0
    loop_idx = 0

    while accumulated < target_sec and loop_idx <= 20:
        for h in highlights:
            if accumulated >= target_sec:
                break
            remaining = target_sec - accumulated
            dur = min(optimal_dur, remaining)
            if dur < 0.3:
                break
            try:
                v = VideoFileClip(h["path"])
                start_time = float(h.get("start", 0))
                end_time   = min(start_time + dur, v.duration)
                if end_time <= start_time:
                    v.close()
                    continue
                clip = v.subclipped(start_time, end_time).resized(height=th)
                if clip.w > tw:
                    clip = clip.cropped(x_center=clip.w / 2, width=tw)
                clip = clip.with_effects([FadeIn(0.15), FadeOut(0.15)])
                if add_watermark and watermark_text.strip():
                    try:
                        txt = (TextClip(
                                text=watermark_text, font_size=28, color="white",
                                font="DejaVu-Sans-Bold", stroke_color="black", stroke_width=1,
                               )
                               .with_position(("right", "bottom"))
                               .with_duration(clip.duration))
                        clip = CompositeVideoClip([clip, txt])
                    except Exception:
                        pass
                clips.append(clip)
                accumulated += clip.duration
                v.close()
                progress_bar.progress(min(accumulated / target_sec, 1.0))
            except Exception as err:
                st.warning(f"Errore clip {h.get('name')}: {err}")
                continue
        loop_idx += 1

    if not clips:
        return None

    sizzle = concatenate_videoclips(clips, method="compose")

    # Colonna sonora opzionale
    if audio_path and os.path.exists(audio_path):
        try:
            bg = (AudioFileClip(audio_path)
                  .subclipped(0, sizzle.duration)
                  .with_effects([AudioFadeOut(1.5)])
                  .with_volume_scaled(0.85))
            final_audio = (CompositeAudioClip([bg, sizzle.audio.with_volume_scaled(0.3)])
                           if sizzle.audio else bg)
            sizzle = sizzle.with_audio(final_audio)
        except Exception as err:
            st.warning(f"Errore audio: {err}")

    out = f"highlights_{int(time.time())}.mp4"
    sizzle.write_videofile(
        out, codec="libx264", audio_codec="aac",
        fps=24, preset="ultrafast", threads=2, logger=None,
    )
    for c in clips:
        try: c.close()
        except Exception: pass
    sizzle.close()
    return out

# ─────────────────────────────────────────
# SIDEBAR — opzioni avanzate
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="sidebar-version">v4.0 · Gemini 2.5 Pro</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">// opzioni avanzate</div>', unsafe_allow_html=True)

    clip_duration = st.slider("Durata base clip (s)", 1.0, 6.0, 2.8, 0.1)
    add_watermark = st.toggle("Watermark", value=False)
    watermark_text = ""
    if add_watermark:
        watermark_text = st.text_input("Testo watermark", value="#HighlightsVD")

    audio_upload = st.file_uploader("Colonna sonora", type=["mp3", "wav", "aac", "m4a"])

    with st.expander("Personalizza prompt AI"):
        custom_prompt = st.text_area("Prompt", value=DEFAULT_PROMPT, height=160)
        st.session_state["_prompt"] = custom_prompt

# ─────────────────────────────────────────
# HERO
# ─────────────────────────────────────────
st.markdown("""
<div class="hero-block">
    <div class="hero-eyebrow">⚡ AI-Powered · Real-time Analysis</div>
    <div class="hero-title">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="hero-sub">Gemini 2.5 Pro · Audio peak detection · Mashup automatico</div>
    <div class="hero-line"></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# STEP 0 — Configurazione e upload
# I widget qui rimangono visibili sempre.
# I valori vengono salvati in session_state subito,
# così sopravvivono ai re-render successivi.
# ─────────────────────────────────────────
st.markdown('<div class="section-label">// configurazione</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    cat_widget = st.selectbox(
        "Tipo contenuto",
        ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"],
        key="w_cat"
    )
with col2:
    plat_widget = st.selectbox(
        "Piattaforma",
        ["Instagram", "TikTok", "Facebook"],
        key="w_plat"
    )
with col3:
    ctype_widget = st.radio(
        "Formato",
        ["Reels", "Storie", "Post"],
        horizontal=True,
        key="w_ctype"
    )

# Salva configurazione in session_state
st.session_state["_cat"]   = cat_widget
st.session_state["_plat"]  = plat_widget
st.session_state["_ctype"] = ctype_widget

st.markdown('<div class="section-label">// carica video</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Video grezzi",
    type=["mp4", "mov"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="w_files"
)

# Quando l'utente carica file, salvali come bytes in session_state
# I bytes sopravvivono ai re-render; gli oggetti UploadedFile no.
if uploaded_files:
    st.session_state["_file_data"] = [
        {"name": f.name, "size": f.size, "bytes": f.getvalue()}
        for f in uploaded_files
    ]

# Leggi sempre da session_state (fonte unica di verità)
file_data  = st.session_state.get("_file_data", [])
cat        = st.session_state.get("_cat",   cat_widget)
plat       = st.session_state.get("_plat",  plat_widget)
ctype      = st.session_state.get("_ctype", ctype_widget)
limit_sec  = PLATFORM_LIMITS[plat][ctype]
prompt     = st.session_state.get("_prompt", DEFAULT_PROMPT)

# ─────────────────────────────────────────
# STEP 1 — Scansione AI
# Appare solo se ci sono file caricati
# ─────────────────────────────────────────
if file_data:
    # Avvisi dimensione
    for f in file_data:
        if f["size"] > 500 * 1024 * 1024:
            st.markdown(
                f'<div class="platform-warning">⚠ {f["name"]} · {f["size"]/1024/1024:.0f} MB — file molto grande</div>',
                unsafe_allow_html=True
            )
    if len(file_data) > MAX_CLIPS:
        st.markdown(
            f'<div class="platform-warning">↳ verranno processati solo i primi {MAX_CLIPS} file</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="section-label">// step 01 — analisi AI</div>', unsafe_allow_html=True)
    col_btn, col_info = st.columns([3, 1])
    with col_btn:
        scan_btn = st.button("⚡ SCANSIONA HIGHLIGHTS", type="primary")
    with col_info:
        st.markdown(
            f'<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;'
            f'color:#3D4455;padding-top:0.8rem;">'
            f'{len(file_data)} FILE · {cat.upper()}</div>',
            unsafe_allow_html=True
        )

    if scan_btn:
        with st.status("Analisi in corso...", expanded=True) as status:
            all_h, temp_paths, errors = [], [], []
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_map = {
                    executor.submit(scan_single_video, f, prompt, cat): f
                    for f in file_data[:MAX_CLIPS]
                }
                for future in concurrent.futures.as_completed(future_map):
                    f_ref = future_map[future]
                    try:
                        result = future.result()
                        if "error" in result:
                            errors.append(result)
                            st.markdown(f'`✗ {result["name"]}` — {result["error"]}')
                        else:
                            all_h.append(result)
                            if result["path"]:
                                temp_paths.append(result["path"])
                            st.markdown(
                                f'`✓ {result["name"]}` '
                                f'— AI: `{result.get("start_ai",0):.1f}s` '
                                f'→ audio peak: `{result["start"]:.1f}s`'
                            )
                    except Exception as err:
                        errors.append({"name": f_ref["name"], "error": str(err)})
            # Salva risultati
            st.session_state["_highlights"]  = all_h
            st.session_state["_temp_paths"]  = temp_paths
            st.session_state["_scan_errors"] = errors
            status.update(
                label=f"✓ {len(all_h)} highlights rilevati",
                state="complete"
            )

# ─────────────────────────────────────────
# STEP 2 — Editor highlights
# Appare appena ci sono risultati in session_state,
# indipendentemente dallo stato del file uploader
# ─────────────────────────────────────────
if st.session_state.get("_highlights"):
    h_list = st.session_state["_highlights"]

    # Retry errori
    if st.session_state.get("_scan_errors"):
        for err_item in st.session_state["_scan_errors"]:
            c1, c2 = st.columns([5, 1])
            c1.markdown(
                f'<div class="platform-warning">✗ {err_item["name"]} — {err_item.get("error","")}</div>',
                unsafe_allow_html=True
            )
            if c2.button("↺ RETRY", key=f"retry_{err_item['name']}"):
                matching = [f for f in file_data if f["name"] == err_item["name"]]
                if matching:
                    with st.spinner(f"Retry {err_item['name']}..."):
                        result = scan_single_video(matching[0], prompt, cat)
                        if "error" not in result:
                            st.session_state["_highlights"].append(result)
                            if result["path"]:
                                st.session_state["_temp_paths"].append(result["path"])
                            st.session_state["_scan_errors"] = [
                                e for e in st.session_state["_scan_errors"]
                                if e["name"] != err_item["name"]
                            ]
                            st.rerun()
                        else:
                            st.error(f"Ancora errore: {result['error']}")

    st.markdown('<div class="section-label">// step 02 — highlights trovati</div>', unsafe_allow_html=True)

    for h in h_list:
        st.markdown(f"""
        <div class="highlight-card">
            <div class="hc-name">▸ {h['name']}</div>
            <div class="hc-reason">{h.get('reason','N/D')}</div>
            <div class="hc-meta">
                AI: <span>{h.get('start_ai',0):.1f}s</span> &nbsp;·&nbsp;
                AUDIO PEAK: <span>{h.get('start',0):.1f}s</span> &nbsp;·&nbsp;
                MUSICA: {h.get('music','—')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("✏ MODIFICA PARAMETRI CLIP"):
        updated = []
        for i, h in enumerate(h_list):
            cols = st.columns([0.5, 1, 1, 2])
            include   = cols[0].checkbox("ON", value=h.get("include", True), key=f"inc_{i}")
            new_start = cols[1].number_input("Inizio (s)", min_value=0.0, value=float(h.get("start",0)), step=0.5, key=f"st_{i}")
            new_dur   = cols[2].number_input("Durata (s)", min_value=0.5, max_value=10.0, value=float(clip_duration), step=0.1, key=f"du_{i}")
            cols[3].caption(f"💡 {h.get('reason','')[:60]}")
            hc = dict(h)
            hc.update({"include": include, "start": new_start, "clip_duration_override": new_dur})
            updated.append(hc)
        st.session_state["_highlights"] = updated

    # Info mashup
    active = [h for h in st.session_state["_highlights"] if h.get("include", True)]
    n_active = len(active)
    base_total = n_active * clip_duration
    repeats = max(1, int(np.ceil(limit_sec / base_total))) if base_total > 0 else 1
    opt_dur = limit_sec / max(1, n_active * repeats)
    st.markdown(
        f'<div class="platform-ok">'
        f'🎬 MASHUP TARGET: <b>{limit_sec:.0f}s</b> · '
        f'{n_active} highlight × {repeats} loop · '
        f'<b>{opt_dur:.1f}s</b> per clip · {plat} {ctype}'
        f'</div>',
        unsafe_allow_html=True
    )
    if h_list:
        st.markdown(
            f'<div class="platform-ok">🎵 MUSICA SUGGERITA: {h_list[0].get("music","N/D")}</div>',
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────
    # STEP 3 — Render
    # ─────────────────────────────────────────
    st.markdown('<div class="section-label">// step 03 — genera mashup</div>', unsafe_allow_html=True)
    col_r, col_i = st.columns([3, 1])
    with col_r:
        render_btn = st.button("▶ GENERA MASHUP FINALE", type="primary")
    with col_i:
        st.markdown(
            f'<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;'
            f'color:#3D4455;padding-top:0.8rem;">'
            f'{n_active} CLIP · {plat.upper()} {ctype.upper()}</div>',
            unsafe_allow_html=True
        )

    if render_btn:
        data_to_render = [h for h in st.session_state["_highlights"] if h.get("include", True)]

        # Salva audio colonna sonora se presente
        audio_path = st.session_state.get("_audio_path")
        if audio_upload and not audio_path:
            ext = os.path.splitext(audio_upload.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as af:
                af.write(audio_upload.getvalue())
                audio_path = af.name
                st.session_state["_audio_path"] = audio_path

        with st.status("Rendering mashup...", expanded=False):
            final_video = render_sizzle(
                data_to_render, plat, ctype, clip_duration,
                add_watermark, watermark_text, audio_path
            )

        if final_video and os.path.exists(final_video):
            st.markdown('<div class="section-label">// output</div>', unsafe_allow_html=True)
            st.video(final_video)

            # Storico
            if "_history" not in st.session_state:
                st.session_state["_history"] = []
            st.session_state["_history"].append({
                "time":     time.strftime("%H:%M:%S"),
                "platform": f"{plat} {ctype}",
                "clips":    len(data_to_render),
                "duration": f"{limit_sec:.0f}s",
            })

            with open(final_video, "rb") as fr:
                st.download_button(
                    "↓ SCARICA MASHUP",
                    fr,
                    file_name="highlights_mashup.mp4",
                    mime="video/mp4"
                )
            try:
                os.unlink(final_video)
            except Exception:
                pass
        else:
            st.error("Errore nella generazione del video.")

# ─────────────────────────────────────────
# STORICO
# ─────────────────────────────────────────
if st.session_state.get("_history"):
    st.markdown('<div class="section-label">// sessione</div>', unsafe_allow_html=True)
    for entry in reversed(st.session_state["_history"]):
        st.markdown(
            f'<div class="history-entry">'
            f'{entry["time"]} · {entry["platform"]} · '
            f'{entry["clips"]} clip · {entry["duration"]}'
            f'</div>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────
# PULIZIA
# ─────────────────────────────────────────
if st.session_state.get("_temp_paths"):
    st.markdown('<div style="margin-top:3rem;"></div>', unsafe_allow_html=True)
    if st.button("✕ PULISCI FILE TEMPORANEI"):
        cleanup_files(st.session_state.get("_temp_paths", []))
        if "_audio_path" in st.session_state:
            cleanup_files([st.session_state.pop("_audio_path")])
        for key in ["_temp_paths", "_highlights", "_scan_errors", "_file_data"]:
            st.session_state.pop(key, None)
        st.success("✓ File temporanei eliminati.")
        st.rerun()
