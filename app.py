import streamlit as st
import tempfile
import os
import json
import time
import concurrent.futures

import numpy as np

# ── NEW SDK (google-genai >= 1.0) ──────────────────────────
from google import genai
from google.genai import types

# ── MOVIEPY 2.x ─────────────────────────────────────────────
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
)
from moviepy.video.fx import FadeIn, FadeOut
from moviepy.audio.fx import AudioFadeOut

# ─────────────────────────────────────────
# STREAMLIT PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Highlights Video Detector",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# STILE GLOBALE
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;600;800&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #080A0F !important;
    color: #E8E8E0 !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #080A0F !important; }
[data-testid="block-container"] { padding: 2rem 2.5rem 4rem !important; }

[data-testid="stSidebar"] {
    background: #0C0E15 !important;
    border-right: 1px solid #1A1F2E !important;
}
[data-testid="stSidebar"] * { font-family: 'DM Mono', monospace !important; }
[data-testid="stSidebarContent"] { padding: 1.5rem 1rem !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #080A0F; }
::-webkit-scrollbar-thumb { background: #00F0D4; border-radius: 2px; }

.hero-block { position: relative; padding: 3rem 0 2.5rem; overflow: hidden; }
.hero-eyebrow {
    font-family: 'DM Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.25em; color: #00F0D4; text-transform: uppercase;
    margin-bottom: 0.6rem; animation: fadeSlideUp 0.6s ease both;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(3.5rem, 8vw, 7rem); line-height: 0.92;
    letter-spacing: 0.02em; color: #FFFFFF;
    animation: fadeSlideUp 0.7s ease 0.1s both;
}
.hero-title span { color: transparent; -webkit-text-stroke: 1.5px #00F0D4; }
.hero-sub {
    font-family: 'Outfit', sans-serif; font-size: 0.9rem; font-weight: 300;
    color: #5A6070; margin-top: 1rem; letter-spacing: 0.04em;
    animation: fadeSlideUp 0.7s ease 0.2s both;
}
.hero-line {
    height: 1px;
    background: linear-gradient(90deg, #00F0D4 0%, #FF2D5533 60%, transparent 100%);
    margin: 2rem 0 0; animation: expandWidth 1s ease 0.4s both;
}
.section-label {
    font-family: 'DM Mono', monospace; font-size: 0.65rem;
    letter-spacing: 0.3em; color: #00F0D4; text-transform: uppercase;
    margin-bottom: 1rem; margin-top: 2.5rem;
    display: flex; align-items: center; gap: 0.6rem;
}
.section-label::after { content: ''; flex: 1; height: 1px; background: #1A1F2E; }

.highlight-card {
    background: #0E1118; border: 1px solid #1A1F2E;
    border-left: 3px solid #00F0D4; border-radius: 6px;
    padding: 1rem 1.2rem; margin-bottom: 0.75rem;
    transition: border-color 0.2s, background 0.2s;
}
.highlight-card:hover { background: #111520; border-left-color: #FF2D55; }
.highlight-card .hc-name { font-family: 'DM Mono', monospace; font-size: 0.78rem; color: #00F0D4; margin-bottom: 0.3rem; }
.highlight-card .hc-reason { font-size: 0.85rem; color: #8891A4; margin-bottom: 0.25rem; }
.highlight-card .hc-meta { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: #3D4455; }
.highlight-card .hc-meta span { color: #FF2D55; }

.platform-warning {
    background: #150A0E; border: 1px solid #FF2D5555;
    border-left: 3px solid #FF2D55; border-radius: 6px;
    padding: 0.9rem 1.2rem; font-family: 'DM Mono', monospace;
    font-size: 0.78rem; color: #FF2D55; margin: 1rem 0;
}
.platform-ok {
    background: #080F0E; border: 1px solid #00F0D433;
    border-left: 3px solid #00F0D4; border-radius: 6px;
    padding: 0.9rem 1.2rem; font-family: 'DM Mono', monospace;
    font-size: 0.78rem; color: #00F0D4; margin: 1rem 0;
}

.stButton > button {
    background: transparent !important; border: 1px solid #00F0D4 !important;
    color: #00F0D4 !important; border-radius: 3px !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    padding: 0.65rem 1.5rem !important; transition: all 0.2s !important; width: 100% !important;
}
.stButton > button:hover { background: #00F0D4 !important; color: #080A0F !important; }
button[kind="primary"] { background: #00F0D4 !important; color: #080A0F !important; border-color: #00F0D4 !important; font-weight: 600 !important; }
button[kind="primary"]:hover { background: #00D4BB !important; }

.stSelectbox > div > div, .stRadio > div, .stSlider > div,
.stTextInput > div > div > input, .stTextArea > div > div > textarea,
.stFileUploader > div {
    background: #0C0E15 !important; border-color: #1A1F2E !important;
    color: #E8E8E0 !important; font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important; border-radius: 4px !important;
}

.stSelectbox label, .stRadio label, .stSlider label,
.stTextInput label, .stTextArea label, .stFileUploader label,
.stToggle label, .stNumberInput label {
    font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important; color: #5A6070 !important;
}

.streamlit-expanderHeader {
    background: #0C0E15 !important; border: 1px solid #1A1F2E !important;
    border-radius: 4px !important; font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important; letter-spacing: 0.08em !important; color: #8891A4 !important;
}
.streamlit-expanderContent {
    background: #0C0E15 !important; border: 1px solid #1A1F2E !important; border-top: none !important;
}

[data-testid="stStatus"] {
    background: #0C0E15 !important; border-color: #1A1F2E !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.78rem !important;
}

hr { border-color: #1A1F2E !important; margin: 1.5rem 0 !important; }

.sidebar-logo { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 0.08em; color: #FFFFFF; margin-bottom: 0.2rem; }
.sidebar-logo span { color: #00F0D4; }
.sidebar-version { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #2A3040; text-transform: uppercase; margin-bottom: 1.5rem; }

.history-entry {
    font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #3D4455;
    border-left: 2px solid #1A1F2E; padding: 0.4rem 0.75rem; margin-bottom: 0.5rem; transition: border-color 0.2s;
}
.history-entry:hover { border-left-color: #00F0D4; color: #8891A4; }

@keyframes fadeSlideUp { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes expandWidth { from { transform: scaleX(0); transform-origin: left; } to { transform: scaleX(1); transform-origin: left; } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.dot-live { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #00F0D4; animation: pulse 1.6s ease infinite; margin-right: 6px; vertical-align: middle; }

.stNumberInput input { background: #0C0E15 !important; border-color: #1A1F2E !important; color: #E8E8E0 !important; font-family: 'DM Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden !important; }
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
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

# Inizializza il client google-genai (nuovo SDK)
@st.cache_resource
def get_genai_client(key: str):
    return genai.Client(api_key=key)

client = get_genai_client(api_key)

# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def save_uploaded_file(uploaded_file) -> str:
    """Salva un UploadedFile Streamlit su disco e ritorna il path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(uploaded_file.getvalue())
        return t.name


def cleanup_files(paths: list):
    """Elimina una lista di file temporanei dal disco."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


def get_audio_peak(video_path: str, start_hint: float = 0.0) -> float:
    """
    Analisi audio-driven: trova il picco RMS nell'intorno ±10s del suggerimento AI.
    Ritorna il timestamp del picco in secondi.
    """
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
        idx_end = int(min(duration, start_hint + 10) / step)
        window = rms_values[idx_start:idx_end]

        if window:
            peak_idx = idx_start + int(np.argmax(window))
        else:
            peak_idx = int(np.argmax(rms_values))

        return float(timestamps[min(peak_idx, len(timestamps) - 1)])

    except Exception:
        return start_hint


def scan_single_video(f, prompt_template: str, cat: str) -> dict:
    """
    Scansiona un singolo video con Gemini (nuovo SDK google-genai).
    Ritorna dict highlight oppure {'error': str, 'name': str}.
    """
    p = save_uploaded_file(f)
    uploaded_file_ref = None

    try:
        # Upload su Gemini Files API (nuovo SDK)
        with open(p, "rb") as fh:
            uploaded_file_ref = client.files.upload(
                file=fh,
                config=types.UploadFileConfig(
                    display_name=f.name,
                    mime_type="video/mp4",
                )
            )

        # Polling stato
        for _ in range(30):  # max 2.5 minuti
            file_info = client.files.get(name=uploaded_file_ref.name)
            if file_info.state.name == "ACTIVE":
                break
            if file_info.state.name == "FAILED":
                raise RuntimeError("Gemini: upload fallito")
            time.sleep(5)

        time.sleep(2)  # piccola pausa di sicurezza

        prompt = prompt_template.replace("{cat}", cat)

        # Chiamata al modello (nuovo SDK)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_uri(
                    file_uri=uploaded_file_ref.uri,
                    mime_type="video/mp4",
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip().replace("```json", "").replace("```", "")
        d = json.loads(raw)

        # Audio-driven refinement
        ai_start = float(d.get("start", 0))
        audio_peak = get_audio_peak(p, start_hint=ai_start)
        d["start_ai"] = ai_start
        d["start"] = audio_peak
        d.update({"path": p, "name": f.name, "include": True, "energy": np.random.uniform(0.5, 1.0)})
        return d

    except Exception as err:
        cleanup_files([p])
        return {"error": str(err), "name": f.name, "path": None}

    finally:
        # Elimina il file da Gemini cloud
        if uploaded_file_ref:
            try:
                client.files.delete(name=uploaded_file_ref.name)
            except Exception:
                pass


def render_sizzle(
    data_to_use: list,
    plat: str,
    ctype: str,
    clip_duration: float,
    add_watermark: bool,
    watermark_text: str,
    audio_path: str | None,
) -> str | None:
    """Rendering finale MoviePy 2.x FIXED."""

    tw, th = FMT[plat][ctype]

    clips = []
    opened_videos = []

    progress_bar = st.progress(0)

    for i, d in enumerate(data_to_use[:MAX_CLIPS]):

        try:
            v = VideoFileClip(d["path"])
            opened_videos.append(v)

            start_time = max(0, float(d.get("start", 0)))
            dur = float(d.get("clip_duration_override", clip_duration))

            end_time = min(start_time + dur, v.duration)

            if end_time <= start_time:
                continue

            clip = v.subclipped(start_time, end_time)

            clip = clip.resized(height=th)

            if clip.w > tw:
                clip = clip.cropped(
                    x_center=clip.w / 2,
                    width=tw
                )

            clip = clip.with_effects([
                FadeIn(0.15),
                FadeOut(0.15)
            ])

            if add_watermark and watermark_text.strip():

                try:
                    txt = (
                        TextClip(
                            text=watermark_text,
                            font_size=28,
                            color="white",
                            font="DejaVu-Sans-Bold",
                            stroke_color="black",
                            stroke_width=1,
                        )
                        .with_position(("right", "bottom"))
                        .with_duration(clip.duration)
                    )

                    clip = CompositeVideoClip([clip, txt])

                except Exception:
                    pass

            clips.append(clip)

        except Exception as err:
            st.warning(f"Errore clip {d.get('name')}: {err}")
            continue

        progress_bar.progress((i + 1) / len(data_to_use))

    if not clips:
        return None

    bg = None
    final_audio = None
    sizzle = None

    try:

        sizzle = concatenate_videoclips(
            clips,
            method="compose",
            padding=-0.15
        )

        total_duration = float(sizzle.duration)

        if (
            audio_path
            and os.path.exists(audio_path)
            and os.path.getsize(audio_path) > 0
        ):

            try:

                bg = AudioFileClip(audio_path)

                if bg.duration > total_duration:
                    bg = bg.subclipped(0, total_duration)
                else:
                    bg = bg.with_duration(total_duration)

                bg = bg.with_start(0)

                bg = bg.with_effects([
                    AudioFadeOut(1.5)
                ])

                bg = bg.with_volume_scaled(0.85)

                if sizzle.audio is not None:

                    orig = (
                        sizzle.audio
                        .with_start(0)
                        .with_duration(total_duration)
                        .with_volume_scaled(0.3)
                    )

                    final_audio = CompositeAudioClip([
                        bg,
                        orig
                    ]).with_duration(total_duration)

                else:
                    final_audio = bg.with_duration(total_duration)

                sizzle = sizzle.with_audio(final_audio)

            except Exception as err:
                st.warning(f"Errore audio: {err}")

        out = f"highlights_{int(time.time())}.mp4"

        sizzle.write_videofile(
            out,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="ultrafast",
            threads=2,
            logger=None,
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
        )

        return out

    except Exception as err:

        st.error(f"Errore rendering: {err}")
        return None

    finally:

        try:
            for c in clips:
                try:
                    c.close()
                except Exception:
                    pass

            try:
                if sizzle:
                    sizzle.close()
            except Exception:
                pass

            try:
                if bg:
                    bg.close()
            except Exception:
                pass

            try:
                if final_audio:
                    final_audio.close()
            except Exception:
                pass

            for v in opened_videos:
                try:
                    v.close()
                except Exception:
                    pass

        except Exception:
            pass


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="sidebar-version">v3.0 · Gemini 2.0 Flash</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">// contenuto</div>', unsafe_allow_html=True)
    cat = st.selectbox("Tipo", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"],
                       label_visibility="collapsed")

    st.markdown('<div class="section-label">// target</div>', unsafe_allow_html=True)
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"],
                        label_visibility="collapsed")
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"], horizontal=True,
                     label_visibility="collapsed")
    limit_sec = PLATFORM_LIMITS[plat][ctype]
    st.markdown(
        f'<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#3D4455;margin-top:0.3rem;">'
        f'MAX {limit_sec}s · {plat} {ctype}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">// clip</div>', unsafe_allow_html=True)
    clip_duration = st.slider("Durata clip (s)", 1.0, 6.0, 2.8, 0.1, label_visibility="collapsed")

    st.markdown('<div class="section-label">// branding</div>', unsafe_allow_html=True)
    add_watermark = st.toggle("Watermark", value=False)
    watermark_text = ""
    if add_watermark:
        watermark_text = st.text_input("Testo watermark", value="#HighlightsVD", label_visibility="collapsed")

    st.markdown('<div class="section-label">// audio</div>', unsafe_allow_html=True)
    audio_upload = st.file_uploader("Colonna sonora", type=["mp3", "wav", "aac", "m4a"],
                                    label_visibility="collapsed")

    st.markdown('<div class="section-label">// ai prompt</div>', unsafe_allow_html=True)
    with st.expander("Personalizza prompt"):
        custom_prompt = st.text_area("Prompt AI", value=DEFAULT_PROMPT, height=160,
                                     label_visibility="collapsed")

    st.markdown('<div class="section-label">// upload</div>', unsafe_allow_html=True)
    files = st.file_uploader("Video grezzi", type=["mp4", "mov"],
                              accept_multiple_files=True, label_visibility="collapsed")

# ─────────────────────────────────────────
# HERO
# ─────────────────────────────────────────
st.markdown("""
<div class="hero-block">
    <div class="hero-eyebrow">⚡ AI-Powered · Real-time Analysis</div>
    <div class="hero-title">HIGHLIGHTS<br><span>VIDEO</span> DETECTOR</div>
    <div class="hero-sub">Gemini 2.0 Flash · Audio peak detection · Montaggio automatico</div>
    <div class="hero-line"></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# LOGICA PRINCIPALE
# ─────────────────────────────────────────
if files:
    for f in files:
        if f.size > 500 * 1024 * 1024:
            st.markdown(
                f'<div class="platform-warning">⚠ {f.name} · {f.size/1024/1024:.0f} MB — file molto grande</div>',
                unsafe_allow_html=True,
            )

    if len(files) > MAX_CLIPS:
        st.markdown(
            f'<div class="platform-warning">↳ {len(files)} file caricati · verranno processati i primi {MAX_CLIPS}</div>',
            unsafe_allow_html=True,
        )

    # Salva audio colonna sonora
    audio_file_path = None
    if audio_upload:
        ext = os.path.splitext(audio_upload.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as af:
            af.write(audio_upload.getvalue())
            audio_file_path = af.name
        st.session_state["audio_path"] = audio_file_path

    # ── STEP 1: SCANSIONE ──────────────────
    st.markdown('<div class="section-label">// step 01 — analisi</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([3, 1])
    with col_a:
        scan_btn = st.button("⚡ SCANSIONA HIGHLIGHTS", type="primary")
    with col_b:
        st.markdown(
            f'<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#3D4455;padding-top:0.8rem;">'
            f'{len(files)} FILE · {cat.upper()}</div>',
            unsafe_allow_html=True,
        )

    if scan_btn:
        all_h, temp_files_scan, errors = [], [], []

        with st.status("Analisi in corso...", expanded=True) as stt:
            st.markdown('<div class="dot-live"></div> scansione in corso...', unsafe_allow_html=True)

            # Parallelo: max 3 thread per non saturare l'API Gemini
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_map = {
                    executor.submit(scan_single_video, f, custom_prompt, cat): f
                    for f in files[:MAX_CLIPS]
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
                                temp_files_scan.append(result["path"])
                            st.markdown(
                                f'`✓ {result["name"]}` '
                                f'— AI: `{result.get("start_ai", 0):.1f}s` '
                                f'→ peak: `{result["start"]:.1f}s`'
                            )
                    except Exception as err:
                        errors.append({"name": f_ref.name, "error": str(err)})

            st.session_state["h_list"] = all_h
            st.session_state["temp_files"] = temp_files_scan
            st.session_state["scan_errors"] = errors
            stt.update(label=f"✓ {len(all_h)} highlights rilevati", state="complete")

    # ── RETRY selettivo ─────────────────────
    if "scan_errors" in st.session_state and st.session_state["scan_errors"]:
        for err_item in st.session_state["scan_errors"]:
            col1, col2 = st.columns([5, 1])
            col1.markdown(
                f'<div class="platform-warning">✗ {err_item["name"]} — {err_item.get("error", "")}</div>',
                unsafe_allow_html=True,
            )
            if col2.button("↺ RETRY", key=f"retry_{err_item['name']}"):
                matching = [f for f in files if f.name == err_item["name"]]
                if matching:
                    with st.spinner(f"Retry {err_item['name']}..."):
                        result = scan_single_video(matching[0], custom_prompt, cat)
                        if "error" not in result:
                            st.session_state["h_list"].append(result)
                            if result["path"]:
                                st.session_state["temp_files"].append(result["path"])
                            st.session_state["scan_errors"] = [
                                e for e in st.session_state["scan_errors"]
                                if e["name"] != err_item["name"]
                            ]
                            st.rerun()
                        else:
                            st.error(f"Ancora errore: {result['error']}")

    # ── STEP 2: EDITOR HIGHLIGHTS ──────────
    if "h_list" in st.session_state and st.session_state["h_list"]:
        h_list = st.session_state["h_list"]

        st.markdown('<div class="section-label">// step 02 — editor highlights</div>', unsafe_allow_html=True)

        for h in h_list:
            st.markdown(f"""
            <div class="highlight-card">
                <div class="hc-name">▸ {h['name']}</div>
                <div class="hc-reason">{h.get('reason', 'N/D')}</div>
                <div class="hc-meta">
                    AI: <span>{h.get('start_ai', 0):.1f}s</span> &nbsp;·&nbsp;
                    AUDIO PEAK: <span>{h.get('start', 0):.1f}s</span> &nbsp;·&nbsp;
                    MUSICA: {h.get('music', '—')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("✏  MODIFICA PARAMETRI CLIP"):
            updated_list = []
            for i, h in enumerate(h_list):
                cols = st.columns([0.5, 1, 1, 1])
                include = cols[0].checkbox("ON", value=h.get("include", True), key=f"inc_{i}")
                cols[0].caption(h["name"][:18])
                new_start = cols[1].number_input("Inizio (s)", min_value=0.0,
                                                  value=float(h.get("start", 0)),
                                                  step=0.5, key=f"start_{i}")
                new_dur = cols[2].number_input("Durata (s)", min_value=0.5, max_value=10.0,
                                               value=float(clip_duration), step=0.1, key=f"dur_{i}")
                cols[3].caption(f"💡 {h.get('reason', '')[:60]}")
                h_copy = dict(h)
                h_copy.update({"include": include, "start": new_start, "clip_duration_override": new_dur})
                updated_list.append(h_copy)
            st.session_state["h_list"] = updated_list

        # Stima durata dinamica e distribuzione intelligente
        active = [d for d in st.session_state["h_list"] if d.get("include", True)]

        target_duration = PLATFORM_LIMITS[plat][ctype]

        if active:

            # assegna energia casuale se assente
            for d in active:
                if "energy" not in d:
                    try:
                        reason_len = len(str(d.get("reason", "")))
                        d["energy"] = min(1.0, max(0.4, reason_len / 100))
                    except Exception:
                        d["energy"] = 0.7

            total_energy = sum(d["energy"] for d in active)

            for d in active:

                weight = d["energy"] / total_energy

                dynamic_duration = target_duration * weight

                # limiti intelligenti
                dynamic_duration = max(1.5, dynamic_duration)
                dynamic_duration = min(20.0, dynamic_duration)

                d["clip_duration_override"] = dynamic_duration

        estimated_sec = sum(
            d.get("clip_duration_override", clip_duration)
            for d in active
        )

        if estimated_sec > limit_sec:
            st.markdown(
                f'<div class="platform-warning">⚠ DURATA STIMATA {estimated_sec:.0f}s — LIMITE {plat} {ctype}: {limit_sec}s</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="platform-ok">✓ DURATA STIMATA {estimated_sec:.0f}s — ENTRO IL LIMITE {plat} {ctype} ({limit_sec}s)</div>',
                unsafe_allow_html=True,
            )

        if active:
            avg_duration = estimated_sec / len(active)

            st.markdown(
                f'<div class="platform-ok">🎬 MASHUP DINAMICO · {len(active)} clip · media {avg_duration:.1f}s per highlight · target {target_duration}s</div>',
                unsafe_allow_html=True,
            )

        if h_list:
            st.markdown(
                f'<div class="platform-ok">🎵 MUSICA SUGGERITA: {h_list[0].get("music", "N/D")}</div>',
                unsafe_allow_html=True,
            )

        # ── STEP 3: RENDER ──────────────────
        st.markdown('<div class="section-label">// step 03 — render</div>', unsafe_allow_html=True)
        col_r, col_info = st.columns([3, 1])
        with col_r:
            render_btn = st.button("▶ GENERA MONTAGGIO FINALE", type="primary")
        with col_info:
            st.markdown(
                f'<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#3D4455;padding-top:0.8rem;">'
                f'{len(active)} CLIP · {plat.upper()} {ctype.upper()}</div>',
                unsafe_allow_html=True,
            )

        if render_btn:
            data_to_use = [d for d in st.session_state["h_list"] if d.get("include", True)]
            audio_path = st.session_state.get("audio_path") or audio_file_path

            with st.status("rendering...", expanded=False):
                final_video = render_sizzle(
                    data_to_use, plat, ctype, clip_duration,
                    add_watermark, watermark_text, audio_path,
                )

            if final_video and os.path.exists(final_video):
                st.markdown('<div class="section-label">// output</div>', unsafe_allow_html=True)
                st.video(final_video)

                if "session_history" not in st.session_state:
                    st.session_state["session_history"] = []
                st.session_state["session_history"].append({
                    "time": time.strftime("%H:%M:%S"),
                    "platform": f"{plat} {ctype}",
                    "clips": len(data_to_use),
                    "duration": f"{estimated_sec:.0f}s",
                })

                with open(final_video, "rb") as fr:
                    st.download_button(
                        "↓ SCARICA VIDEO",
                        fr,
                        file_name="highlights_output.mp4",
                        mime="video/mp4",
                    )
                try:
                    os.unlink(final_video)
                except Exception:
                    pass
            else:
                st.error("Errore nella generazione del video.")

    # ── STORICO ─────────────────────────────
    if "session_history" in st.session_state and st.session_state["session_history"]:
        st.markdown('<div class="section-label">// sessione</div>', unsafe_allow_html=True)
        for entry in reversed(st.session_state["session_history"]):
            st.markdown(
                f'<div class="history-entry">'
                f'{entry["time"]} · {entry["platform"]} · {entry["clips"]} clip · {entry["duration"]}'
                f'</div>',
                unsafe_allow_html=True,
            )



# ─────────────────────────────────────────
# GOOGLE CLOUD CLEANUP
# ─────────────────────────────────────────
with st.sidebar:

    st.markdown('<div class="section-label">// cloud cleanup</div>', unsafe_allow_html=True)

    if st.button("☁ ELIMINA FILE GEMINI CLOUD"):

        deleted_count = 0
        failed_count = 0

        try:

            files_list = client.files.list()

            for f in files_list:

                try:
                    client.files.delete(name=f.name)
                    deleted_count += 1
                except Exception:
                    failed_count += 1

            if deleted_count > 0:
                st.success(f"Eliminati {deleted_count} file dal cloud Gemini.")

            if failed_count > 0:
                st.warning(f"{failed_count} file non eliminati.")

            if deleted_count == 0 and failed_count == 0:
                st.info("Nessun file presente nel cloud Gemini.")

        except Exception as err:
            st.error(f"Errore cleanup cloud: {err}")


# ── PULIZIA ─────────────────────────────────
if "temp_files" in st.session_state and st.session_state["temp_files"]:
    st.markdown('<div style="margin-top:3rem;"></div>', unsafe_allow_html=True)
    if st.button("✕ PULISCI FILE TEMPORANEI"):
        cleanup_files(st.session_state["temp_files"])
        if "audio_path" in st.session_state:
            cleanup_files([st.session_state.pop("audio_path")])
        for key in ["temp_files", "h_list", "scan_errors"]:
            st.session_state.pop(key, None)
        st.success("File temporanei eliminati.")
