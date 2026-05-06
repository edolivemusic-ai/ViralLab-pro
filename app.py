import streamlit as st
import google.generativeai as genai
import moviepy.editor as mp
import tempfile
import os
import json
import time
import concurrent.futures

import PIL.Image
import numpy as np

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
    .platform-warning { background-color: #2a1f0f; border-left: 4px solid #FF0050; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Puglia Sizzle Lab: Highlight Editor ☀️")

# --- API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Manca GEMINI_API_KEY nei Secrets di Streamlit.")
    st.stop()

# Configure with explicit API version
genai.configure(api_key=api_key, transport="rest")

# --- COSTANTI ---
MAX_CLIPS = 10

# --- LIMITI PIATTAFORMA (secondi) ---
PLATFORM_LIMITS = {
    "Instagram": {"Reels": 90,  "Storie": 60,  "Post": 60},
    "TikTok":    {"Reels": 180, "Storie": 60,  "Post": 180},
    "Facebook":  {"Reels": 60,  "Storie": 20,  "Post": 240},
}

# --- FORMATI RISOLUZIONE ---
FMT = {
    "Instagram": {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 900)},
    "TikTok":    {"Reels": (720, 1280), "Storie": (720, 1280), "Post": (720, 1280)},
    "Facebook":  {"Post":  (720, 720),  "Reels":  (720, 1280), "Storie": (720, 1280)}
}

# --- DEFAULT PROMPT ---
DEFAULT_PROMPT = (
    "Sei un video editor professionista di Bari specializzato in contenuti virali Puglia. "
    "Analizza questo video di {cat} e trova il momento di picco energetico "
    "(drop, acuto, brindisi, emozione forte). "
    "Rispondi SOLO con JSON valido, senza markdown, senza backtick: "
    '{"start": float, "reason": "breve spiegazione", "music": "3 canzoni trend Italia"}'
)


# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def save_uploaded_file(uploaded_file):
    """Salva il file caricato e restituisce il percorso temporaneo."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(uploaded_file.getvalue())
        return t.name


def cleanup_temp_files(paths):
    """Elimina una lista di file temporanei dal disco."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


def get_audio_peak(video_path, start_hint=0.0):
    """
    Analisi audio-driven: trova il secondo con il picco di volume RMS
    nell'intorno del suggerimento AI (±10s).
    Ritorna il secondo di inizio del picco.
    """
    try:
        v = mp.VideoFileClip(video_path)
        if v.audio is None:
            v.close()
            return start_hint

        duration = v.duration
        step = 0.5
        timestamps = np.arange(0, duration - step, step)

        rms_values = []
        for t in timestamps:
            chunk = v.audio.subclip(t, min(t + step, duration))
            samples = chunk.to_soundarray(fps=22050)
            rms = np.sqrt(np.mean(samples ** 2))
            rms_values.append(rms)

        v.close()

        # Cerca il picco nell'intorno ±10s del suggerimento AI
        window_start = max(0, start_hint - 10)
        window_end = min(duration, start_hint + 10)
        idx_start = int(window_start / step)
        idx_end = int(window_end / step)

        window_rms = rms_values[idx_start:idx_end]
        if window_rms:
            peak_idx = idx_start + int(np.argmax(window_rms))
            return float(timestamps[peak_idx])
        else:
            return float(timestamps[int(np.argmax(rms_values))])

    except Exception:
        return start_hint


def scan_single_video(f, model, prompt_template, cat):
    """
    Scansiona un singolo file video con Gemini.
    Usato per processing parallelo e retry selettivo.
    Ritorna dict con highlight oppure {'error': str, 'name': str}.
    """
    p = save_uploaded_file(f)
    v_ai = None
    try:
        v_ai = genai.upload_file(path=p)

        while genai.get_file(v_ai.name).state.name == "PROCESSING":
            time.sleep(4)
            v_ai = genai.get_file(v_ai.name)

        time.sleep(2)

        prompt = prompt_template.replace("{cat}", cat)
        r = model.generate_content(
            [v_ai, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        raw = r.text.strip().replace("```json", "").replace("```", "")
        d = json.loads(raw)

        # 🎵 Audio-driven refinement
        ai_start = float(d.get('start', 0))
        audio_peak = get_audio_peak(p, start_hint=ai_start)
        d['start_ai'] = ai_start
        d['start'] = audio_peak
        d.update({'path': p, 'name': f.name, 'include': True})
        return d

    except Exception as err:
        cleanup_temp_files([p])
        return {'error': str(err), 'name': f.name, 'path': None}
    finally:
        if v_ai:
            try:
                genai.delete_file(v_ai.name)
            except Exception:
                pass


def render_sizzle(data_to_use, plat, ctype, clip_duration,
                  add_watermark, watermark_text, audio_path):
    """Rendering finale del video sizzle con tutte le opzioni."""
    tw, th = FMT[plat][ctype]
    clips = []
    progress_bar = st.progress(0)

    for i, d in enumerate(data_to_use[:MAX_CLIPS]):
        try:
            v = mp.VideoFileClip(d['path'])
            start_time = float(d.get('start', 0))
            dur = float(d.get('clip_duration_override', clip_duration))
            end_time = min(start_time + dur, v.duration)

            clip = v.subclip(start_time, end_time).resize(height=th)
            final_clip = clip.crop(x_center=clip.w / 2, width=tw) if clip.w > tw else clip
            final_clip = final_clip.fadein(0.15).fadeout(0.15)

            # 🎨 Watermark
            if add_watermark and watermark_text.strip():
                try:
                    txt_clip = (mp.TextClip(watermark_text, fontsize=28, color='white',
                                            font='DejaVu-Sans-Bold', stroke_color='black', stroke_width=1)
                                .set_position(('right', 'bottom'))
                                .set_duration(final_clip.duration)
                                .margin(right=12, bottom=12, opacity=0))
                    final_clip = mp.CompositeVideoClip([final_clip, txt_clip])
                except Exception:
                    pass

            clips.append(final_clip)
            v.close()
        except Exception as err:
            st.warning(f"Errore clip {d.get('name')}: {err}")
            continue
        progress_bar.progress((i + 1) / len(data_to_use))

    if not clips:
        return None

    sizzle = mp.concatenate_videoclips(clips, method="compose")
    total_duration = sizzle.duration

    # 🔊 Colonna sonora
    if audio_path and os.path.exists(audio_path):
        try:
            bg_audio = mp.AudioFileClip(audio_path).subclip(0, total_duration).audio_fadeout(1.5)
            if sizzle.audio:
                orig_audio = sizzle.audio.volumex(0.3)
                final_audio = mp.CompositeAudioClip([bg_audio.volumex(0.85), orig_audio])
            else:
                final_audio = bg_audio
            sizzle = sizzle.set_audio(final_audio)
        except Exception as err:
            st.warning(f"Errore audio colonna sonora: {err}")

    out = f"puglia_sizzle_{int(time.time())}.mp4"
    sizzle.write_videofile(out, codec="libx264", audio_codec="aac",
                           fps=24, preset='ultrafast', threads=2, logger=None)
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    sizzle.close()
    return out


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.header("📍 Bari/Puglia Config")

    cat = st.selectbox("Tipo Contenuto", ["DJ Set", "Musica dal Vivo", "Karaoke", "Wedding Music", "Wedding Band"])
    plat = st.selectbox("Piattaforma", ["Instagram", "TikTok", "Facebook"])
    ctype = st.radio("Formato", ["Reels", "Storie", "Post"])

    limit_sec = PLATFORM_LIMITS[plat][ctype]
    st.caption(f"⏱️ Durata max consigliata per {plat} {ctype}: **{limit_sec}s**")

    st.divider()

    # ✂️ Durata clip con slider
    clip_duration = st.slider(
        "✂️ Durata ogni clip (secondi)",
        min_value=1.0, max_value=6.0, value=2.8, step=0.1,
        help="Clip più brevi = ritmo veloce. Clip più lunghe = più contesto."
    )

    st.divider()

    # 🎨 Watermark / branding
    add_watermark = st.toggle("🎨 Aggiungi watermark/branding", value=False)
    watermark_text = ""
    if add_watermark:
        watermark_text = st.text_input("Testo watermark", value="#PugliaSizzle")

    st.divider()

    # 🔊 Colonna sonora
    audio_upload = st.file_uploader(
        "🔊 Colonna sonora (opzionale)",
        type=["mp3", "wav", "aac", "m4a"],
        help="Verrà mixata sui clip. L'audio originale resterà a volume ridotto (30%)."
    )

    st.divider()

    # 🧠 Prompt personalizzabile
    with st.expander("🧠 Personalizza prompt AI"):
        custom_prompt = st.text_area(
            "Prompt Gemini",
            value=DEFAULT_PROMPT,
            height=180,
            help="Usa {cat} come placeholder per il tipo di contenuto."
        )

    st.divider()

    files = st.file_uploader(
        "📤 Carica i video grezzi",
        type=["mp4", "mov"],
        accept_multiple_files=True,
        help=f"⚠️ Dimensione consigliata: fino a 400-500 MB. Max {MAX_CLIPS} clip processati."
    )


# ─────────────────────────────────────────
# LOGICA PRINCIPALE
# ─────────────────────────────────────────
if files:
    for f in files:
        if f.size > 500 * 1024 * 1024:
            st.warning(f"⚠️ **{f.name}** è molto grande ({f.size / 1024 / 1024:.1f} MB).")

    if len(files) > MAX_CLIPS:
        st.info(f"ℹ️ Verranno processati solo i primi {MAX_CLIPS} video.")

    # Salva audio colonna sonora in temp
    audio_file_path = None
    if audio_upload:
        ext = os.path.splitext(audio_upload.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as af:
            af.write(audio_upload.getvalue())
            audio_file_path = af.name
        st.session_state['audio_path'] = audio_file_path

    # ── STEP 1: SCANSIONE PARALLELA ────────
    if st.button("🔎 1. SCANSIONA HIGHLIGHTS ED ENERGIA", type="primary"):
        all_h = []
        temp_files_scan = []
        errors = []

        with st.status("🛸 AI sta analizzando in parallelo...", expanded=True) as stt:
            try:
                # Try to list available models first
                models = genai.list_models()
                model_names = [m.name for m in models]
                stt.write(f"📋 Modelli disponibili: {model_names}")
                
                # Use the first available model that supports generateContent
                model_name = None
                for model in models:
                    if 'generateContent' in model.supported_generation_methods:
                        model_name = model.name.split('/')[-1]
                        break
                
                if not model_name:
                    model_name = 'gemini-pro'  # fallback
                
                stt.write(f"🎯 Usando modello: {model_name}")
                model = genai.GenerativeModel(model_name)
            except Exception as e:
                stt.write(f"⚠️ Errore nel caricare modelli: {e}")
                model = genai.GenerativeModel('gemini-pro')
            
            files_to_scan = files[:MAX_CLIPS]

            # ⚡ Processing parallelo (max 3 thread simultanei per non saturare l'API)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_map = {
                    executor.submit(scan_single_video, f, model, custom_prompt, cat): f
                    for f in files_to_scan
                }
                for future in concurrent.futures.as_completed(future_map):
                    f_ref = future_map[future]
                    try:
                        result = future.result()
                        if 'error' in result:
                            errors.append(result)
                            stt.write(f"❌ Errore su **{result['name']}**: {result['error']}")
                        else:
                            all_h.append(result)
                            if result['path']:
                                temp_files_scan.append(result['path'])
                            stt.write(
                                f"✅ **{result['name']}** → "
                                f"AI: {result.get('start_ai', '?'):.1f}s | "
                                f"🎵 Audio peak: {result['start']:.1f}s"
                            )
                    except Exception as err:
                        errors.append({'name': f_ref.name, 'error': str(err)})

            st.session_state['h_list'] = all_h
            st.session_state['temp_files'] = temp_files_scan
            st.session_state['scan_errors'] = errors
            stt.update(label="✅ Analisi completata!", state="complete")

    # ── RETRY selettivo ────────────────────
    if 'scan_errors' in st.session_state and st.session_state['scan_errors']:
        st.warning(f"⚠️ {len(st.session_state['scan_errors'])} video non scansionati.")
        for err_item in st.session_state['scan_errors']:
            col1, col2 = st.columns([4, 1])
            col1.write(f"❌ **{err_item['name']}**: {err_item.get('error', 'Errore sconosciuto')}")
            if col2.button("🔄 Riprova", key=f"retry_{err_item['name']}"):
                matching = [f for f in files if f.name == err_item['name']]
                if matching:
                    with st.spinner(f"Riprovando {err_item['name']}..."):
                        model = genai.GenerativeModel('gemini-pro')
                        result = scan_single_video(matching[0], model, custom_prompt, cat)
                        if 'error' not in result:
                            st.session_state['h_list'].append(result)
                            if result['path']:
                                st.session_state['temp_files'].append(result['path'])
                            st.session_state['scan_errors'] = [
                                e for e in st.session_state['scan_errors']
                                if e['name'] != err_item['name']
                            ]
                            st.success(f"✅ {err_item['name']} scansionato!")
                            st.rerun()
                        else:
                            st.error(f"Ancora errore: {result['error']}")

    # ── STEP 2: PREVIEW INTERATTIVA ────────
    if 'h_list' in st.session_state and st.session_state['h_list']:
        h_list = st.session_state['h_list']
        st.success(f"🔥 Isolati **{len(h_list)}** highlights forti!")

        # 📊 Editor pre-montaggio
        with st.expander("✏️ Modifica Highlights prima del montaggio", expanded=True):
            st.caption("Includi/escludi clip, modifica il punto di inizio e la durata di ciascuna.")
            updated_list = []
            for i, h in enumerate(h_list):
                st.markdown(f"**{i+1}. {h['name']}**")
                cols = st.columns([1, 1, 1, 2])

                include = cols[0].checkbox("Includi", value=h.get('include', True), key=f"inc_{i}")
                new_start = cols[1].number_input(
                    "Inizio (s)", min_value=0.0, value=float(h.get('start', 0)),
                    step=0.5, key=f"start_{i}"
                )
                new_dur = cols[2].number_input(
                    "Durata (s)", min_value=0.5, max_value=10.0, value=float(clip_duration),
                    step=0.1, key=f"dur_{i}"
                )
                cols[3].caption(f"💡 {h.get('reason', 'N/D')}")
                if h.get('start_ai') is not None:
                    cols[3].caption(f"🤖 AI: {h['start_ai']:.1f}s → 🎵 Peak audio: {h['start']:.1f}s")

                h_copy = dict(h)
                h_copy.update({'include': include, 'start': new_start, 'clip_duration_override': new_dur})
                updated_list.append(h_copy)
                st.divider()

            st.session_state['h_list'] = updated_list

        # Stima durata e warning piattaforma
        active = [d for d in st.session_state['h_list'] if d.get('include', True)]
        estimated_sec = sum(d.get('clip_duration_override', clip_duration) for d in active)
        limit_sec = PLATFORM_LIMITS[plat][ctype]

        if estimated_sec > limit_sec:
            st.markdown(
                f'<div class="platform-warning">⚠️ Durata stimata: <b>{estimated_sec:.1f}s</b> — '
                f'supera il limite consigliato di <b>{limit_sec}s</b> per {plat} {ctype}.</div>',
                unsafe_allow_html=True
            )
        else:
            st.info(f"⏱️ Durata stimata: **{estimated_sec:.1f}s** — entro il limite {plat} {ctype} ({limit_sec}s) ✅")

        if h_list:
            st.info(f"🎵 **Musica suggerita:** {h_list[0].get('music', 'Non disponibile')}")

        # ── STEP 3: GENERA ─────────────────
        if st.button("🎬 2. GENERA MONTAGGIO FINALE", type="primary"):
            data_to_use = [d for d in st.session_state['h_list'] if d.get('include', True)]
            audio_path = st.session_state.get('audio_path') or audio_file_path

            with st.status("✂️ Creazione montaggio ritmico..."):
                final_video = render_sizzle(
                    data_to_use, plat, ctype, clip_duration,
                    add_watermark, watermark_text, audio_path
                )

            if final_video and os.path.exists(final_video):
                st.video(final_video)

                # 🗂️ Aggiungi allo storico
                if 'session_history' not in st.session_state:
                    st.session_state['session_history'] = []
                st.session_state['session_history'].append({
                    'time': time.strftime("%H:%M:%S"),
                    'platform': f"{plat} {ctype}",
                    'clips': len(data_to_use),
                    'duration': f"{estimated_sec:.1f}s"
                })

                with open(final_video, "rb") as fr:
                    st.download_button(
                        "📥 SCARICA VIDEO PRONTO",
                        fr,
                        file_name="puglia_sizzle_pro.mp4",
                        mime="video/mp4"
                    )
                try:
                    os.unlink(final_video)
                except Exception:
                    pass
            else:
                st.error("Errore nella generazione del video.")

    # 🗂️ Storico sessione
    if 'session_history' in st.session_state and st.session_state['session_history']:
        with st.expander(f"🗂️ Storico sessione ({len(st.session_state['session_history'])} montaggi)"):
            for entry in reversed(st.session_state['session_history']):
                st.write(
                    f"⏰ **{entry['time']}** — {entry['platform']} — "
                    f"{entry['clips']} clip — {entry['duration']}"
                )


# ─────────────────────────────────────────
# PULIZIA
# ─────────────────────────────────────────
if 'temp_files' in st.session_state and st.session_state['temp_files']:
    if st.button("🧹 Pulisci file temporanei"):
        cleanup_temp_files(st.session_state['temp_files'])
        if 'audio_path' in st.session_state:
            cleanup_temp_files([st.session_state.pop('audio_path')])
        st.success("✅ File temporanei eliminati.")
        for key in ['temp_files', 'h_list', 'scan_errors']:
            st.session_state.pop(key, None)
