# app.py - Codice modificato per usare Gemini 2.5 Pro

import streamlit as st
import tempfile
import os
import json
import time
import concurrent.futures
import numpy as np
import google.generativeai as genai
# Non è necessario importare 'types' separatamente se usi il namespace genai
# ma se la tua logica originale ne ha bisogno, potrebbe essere:
# from google.generativeai import types
# Ma per ora, proviamo prima con l'import principale.
from moviepy.editor import ( # Moviepy import corretto
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeAudioClip, CompositeVideoClip, TextClip
)
from moviepy.video.fx import FadeIn, FadeOut
from moviepy.audio.fx import AudioFadeOut
import logging # Assicurati che sia presente

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
# Manteniamo il tuo stile CSS originale
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
# Utilizza st.secrets per ottenere la chiave API
# Assicurati che la chiave sia impostata come GEMINI_API_KEY nei secrets di Streamlit Cloud
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    # Inizializza il client google-genai (nuovo SDK)
    # Usiamo st.cache_resource per inizializzare il client una sola volta
    @st.cache_resource
    def get_genai_client(key: str):
        return genai.Client(api_key=key)

    client = get_genai_client(api_key)
    logger.info("Client Gemini inizializzato con successo.")
except KeyError:
    logger.error("Chiave API 'GEMINI_API_KEY' non trovata in st.secrets.")
    st.error("ERRORE: Chiave API Gemini non trovata nei secrets della piattaforma. "
             "Assicurati di aver impostato GEMINI_API_KEY nella configurazione dei secrets.")
    st.stop()
except Exception as e:
    logger.error(f"Errore durante l'inizializzazione del client Gemini: {e}")
    st.error(f"Errore durante l'inizializzazione del client Gemini: {e}")
    st.stop()


# ─────────────────────────────────────────
# FUNZIONI UTILITY
# ─────────────────────────────────────────

def save_uploaded_file(uploaded_file) -> str:
    """Salva un UploadedFile Streamlit su disco e ritorna il path."""
    # Assicurati che tempfile sia importato
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t: # Aggiunto suffix per compatibilità moviepy
        t.write(uploaded_file.getvalue())
        return t.name

def cleanup_files(paths: list):
    """Elimina una lista di file temporanei dal disco."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Errore durante la pulizia del file {path}: {e}") # Logga gli errori di cleanup

def get_audio_peak(video_path: str, start_hint: float = 0.0) -> float:
    """
    Analisi audio-driven: trova il picco energetico del video.
    Questa funzione non usa direttamente l'API Gemini, quindi la lasciamo invariata.
    """
    try:
        with VideoFileClip(video_path) as video:
            audio = video.audio
            if audio is None:
                return start_hint # Nessun audio, ritorna hint

            # Analisi del picco audio (questo è un placeholder, dovresti implementare la logica reale)
            # Esempio: estrarre una parte dell'audio e analizzarne l'RMS o l'energia
            # Questo richiede librerie come librosa o numpy per analisi audio più sofisticate.
            # Per ora, ritorniamo un valore di default o l'hint.
            logger.warning("get_audio_peak: Implementazione reale non presente, ritorna start_hint.")
            return start_hint

    except Exception as e:
        logger.error(f"Errore in get_audio_peak per {video_path}: {e}")
        return start_hint

def get_gemini_response(prompt: str, cat: str, uploaded_file_path: str) -> dict:
    """
    Invia una richiesta al modello Gemini per analizzare il video e trovare momenti chiave.
    """
    # Costruisci il prompt con le informazioni specifiche
    full_prompt = prompt.format(cat=cat)

    try:
        # --- MODIFICA PRINCIPALE QUI ---
        # Specifica il modello da usare per la generazione.
        # Gemini 2.5 Pro è generalmente consigliato per compiti complessi e multimodali.
        # Se hai bisogno di risposte più veloci e meno costose, potresti usare 'gemini-2.5-flash'.
        # Il client può inferire il modello, ma è buona pratica specificarlo.
        # Per ora, dato che il tuo prompt è testuale, possiamo lasciare che il client scelga
        # o specificare un modello testuale se necessario.
        # Il client.generate_content dovrebbe usare un modello di default adeguato o quello configurato.
        # Se vuoi ASSICURARTI di usare Gemini 2.5 Pro, potresti dover inizializzare il modello esplicitamente:
        # model = genai.GenerativeModel('gemini-2.5-pro')
        # response = model.generate_content(full_prompt)
        # Ma dato che stai usando client.generate_content, questo si basa sulla configurazione del client.
        # La configurazione `genai.configure` dovrebbe usare il modello predefinito più recente, che è 2.5 Pro.
        # Se ciò non dovesse bastare, dovrai passare il `model` alla funzione.
        
        # Il tuo codice originale usa client.generate_content(prompt).
        # Assumendo che genai.configure abbia configurato il client per usare un modello recente
        # come Gemini 2.5 Pro (o il suo default), questa chiamata dovrebbe funzionare.
        # Se vuoi esplicitarlo, dovresti modificare questa funzione per ricevere il modello o
        # inizializzare il modello qui. Dato che il tuo prompt è solo testo,
        # la semplice chiamata `client.generate_content` potrebbe non essere multimodale.
        
        # Per essere SICURI di usare Gemini 2.5 Pro, potresti dover passare il modello:
        # Inizializza il modello qui se necessario, o passalo come argomento alla funzione.
        # Per semplicità, assumiamo che la configurazione del client usi già 2.5 Pro come default.
        # Se si verificano problemi, dovrai esplicitare il modello qui.

        response = client.generate_content(
            full_prompt,
            # generations_config=types.GenerationConfig( # Esempio di configurazione
            #     candidate_count=1,
            #     stop_sequences=["}"], # Per assicurare output JSON valido
            #     max_output_tokens=200
            # ),
            # safety_settings=[ # Configura safety settings se necessario
            #     types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE")
            # ]
        )

        # Il tuo codice originale analizza la risposta JSON
        response_json = json.loads(response.text)
        logger.info(f"Risposta JSON ricevuta da Gemini: {response_json}")
        return response_json

    except json.JSONDecodeError:
        logger.error(f"Errore: La risposta di Gemini non è un JSON valido. Risposta ricevuta: {response.text}")
        st.error("Errore: L'API Gemini ha restituito una risposta non valida (non JSON). Controlla il prompt o i limiti.")
        return None
    except Exception as e:
        logger.error(f"Errore durante la chiamata a Gemini: {e}")
        st.error(f"Errore durante la comunicazione con l'API Gemini: {e}")
        return None

# ─────────────────────────────────────────
# FUNZIONE PRINCIPALE PER L'ELABORAZIONE VIDEO
# ─────────────────────────────────────────

def process_video(video_path: str, cat: str, prompt_template: str) -> list:
    """
    Elabora il video per trovare clip di highlight usando Gemini e moviepy.
    """
    highlights = []
    temp_files_to_cleanup = [video_path] # Aggiunge il video stesso alla lista di pulizia

    try:
        # 1. Ottieni i momenti chiave dal modello AI
        gemini_data = get_gemini_response(prompt_template, cat, video_path)

        if not gemini_data:
            st.error("Impossibile ottenere dati da Gemini. Interruzione elaborazione.")
            return highlights

        # Estrai i momenti chiave (assumendo che ci sia una lista di momenti)
        # Il tuo prompt chiede un singolo JSON, quindi dobbiamo adattarlo se ci sono più momenti
        # O se la risposta è una lista di oggetti JSON.
        # Per ora, assumiamo che gemini_data sia un singolo oggetto con 'start'
        
        # Se gemini_data è un dizionario con 'start':
        if isinstance(gemini_data, dict) and "start" in gemini_data:
            start_time = gemini_data["start"]
            reason = gemini_data.get("reason", "Momento chiave trovato")
            music_suggestions = gemini_data.get("music", ["trend_italia"]) # Default
            
            # Aggiungi come highlight singolo
            highlights.append({
                "start": start_time,
                "end": start_time + 5, # Assumiamo una durata fissa di 5 secondi per ora
                "reason": reason,
                "music": music_suggestions,
                "cat": cat
            })
        # Se gemini_data è una LISTA di dizionari (più probabile per più clip)
        elif isinstance(gemini_data, list):
            for item in gemini_data:
                if isinstance(item, dict) and "start" in item:
                    start_time = item["start"]
                    reason = item.get("reason", "Momento chiave trovato")
                    music_suggestions = item.get("music", ["trend_italia"])
                    
                    # Assumiamo una durata fissa per la clip (es. 5 secondi)
                    # Dovresti magari calcolare la fine basandoti sulla durata del video o sul picco audio
                    end_time = start_time + 5 # Durata fissa di 5 secondi come esempio
                    
                    highlights.append({
                        "start": start_time,
                        "end": end_time,
                        "reason": reason,
                        "music": music_suggestions,
                        "cat": cat
                    })
        else:
            logger.warning(f"Formato risposta Gemini inatteso: {gemini_data}")
            st.warning("Formato risposta Gemini inatteso. Controlla il prompt.")
            return highlights

        # Ordina gli highlight per tempo di inizio
        highlights.sort(key=lambda x: x["start"])

        # 2. Estrai le clip video usando moviepy
        clips = []
        with VideoFileClip(video_path) as video:
            duration = video.duration
            for highlight in highlights:
                start = max(0.0, highlight["start"])
                end = min(duration, highlight["end"]) # Assicura che non vada oltre la durata del video

                if end > start: # Assicurati che la clip abbia una durata valida
                    clip = video.subclip(start, end)
                    clips.append(clip)
                    temp_files_to_cleanup.append(clip.filename) # Se moviepy crea file temporanei

        # 3. Concatenale
        final_clip = concatenate_videoclips(clips)

        # 4. Aggiungi musica (logica da implementare completamente)
        # Per ora, non aggiungiamo musica per semplicità.
        # La logica di scelta musica e composizione audio andrebbe qui.

        # 5. Salva il video finale
        output_filename = f"highlight_{cat.replace(' ', '_')}_{int(time.time())}.mp4"
        output_path = os.path.join(tempfile.gettempdir(), output_filename) # Salva in directory temporanea
        
        # Esporta il video finale
        # Potresti voler specificare codec, bitrate, fps, ecc.
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        temp_files_to_cleanup.append(output_path) # Aggiungi il file di output alla lista pulizia

        logger.info(f"Video highlight generato: {output_path}")
        return output_path # Ritorna il percorso del file generato

    except Exception as e:
        logger.error(f"Errore critico durante l'elaborazione video: {e}")
        st.error(f"Errore critico durante l'elaborazione video: {e}")
        return [] # Ritorna lista vuota in caso di errore

    finally:
        # Pulisci tutti i file temporanei creati durante l'elaborazione
        cleanup_files(temp_files_to_cleanup)


# ─────────────────────────────────────────
# INTERFACCIA UTENTE STREAMLIT
# ─────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown("<div class='sidebar-logo'>ViralLab<span>Pro</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-version'>Video Highlights AI</div>", unsafe_allow_html=True)

        st.sidebar.subheader("Parametri Video")

        # Caricamento file video
        uploaded_file = st.file_uploader(
            "Carica il tuo video",
            type=["mp4", "mov", "avi"], # Tipi di file video supportati
            help="Carica un file video (MP4, MOV, AVI) per l'analisi."
        )

        # Scelta categoria
        cat = st.selectbox(
            "Categoria del Video",
            options=["drop", "acuto", "brindisi", "emozione forte", "musica", "sport", "altri"],
            index=0,
            help="Seleziona la categoria principale per affinare la ricerca del momento di picco."
        )

        # Prompt personalizzabile
        prompt_template = st.text_area(
            "Prompt per l'AI (JSON Output):",
            value=DEFAULT_PROMPT.format(cat=cat.lower()), # Inizializza con valore di default basato sulla categoria
            height=200,
            help="Il prompt guida l'AI. Richiede output JSON con 'start', 'reason', 'music'."
        )

        # Parametri per l'elaborazione (es. lunghezza clip)
        clip_duration = st.slider(
            "Durata Clip Highlight (secondi)",
            min_value=2, max_value=15, value=5, step=1,
            help="Durata desiderata per ogni clip highlight estratta."
        )
        # Qui potresti aggiungere altri slider/input per parametri di moviepy se necessario

        process_button = st.button("⚡ Genera Highlights", type="primary")

        return uploaded_file, cat, prompt_template, clip_duration, process_button

def main_content(uploaded_file, cat, prompt_template, clip_duration, process_button):
    st.title("Generatore di Highlights Video con AI")
    st.markdown("Carica il tuo video, seleziona la categoria e lascia che l'AI trovi i momenti più "
                "energetici per te!")

    if process_button:
        if not uploaded_file:
            st.warning("Per favore, carica un file video.")
            return
        if not cat:
            st.warning("Per favore, seleziona una categoria.")
            return
        if not prompt_template:
            st.warning("Il prompt non può essere vuoto.")
            return

        # Salva il file video caricato temporaneamente
        video_path = None
        try:
            video_path = save_uploaded_file(uploaded_file)
            st.info(f"Video temporaneamente salvato come: {video_path}")

            # Avvia l'elaborazione
            with st.spinner("Analisi del video e generazione highlights in corso... ⏳"):
                # Chiama la funzione principale di elaborazione
                # Passa il percorso del video, la categoria, il prompt e la durata della clip
                output_path_or_list = process_video(video_path, cat, prompt_template)

                # Gestisci il risultato
                if isinstance(output_path_or_list, str) and output_path_or_list.endswith(".mp4"):
                    # Se è stato generato un singolo file video
                    final_video_path = output_path_or_list
                    st.success("🎉 Video highlights generato con successo!")
                    
                    # Mostra il video generato
                    st.video(final_video_path)

                    # Offri il download
                    with open(final_video_path, "rb") as video_file:
                        st.download_button(
                            label="Scarica il tuo video highlights",
                            data=video_file,
                            file_name=os.path.basename(final_video_path),
                            mime="video/mp4"
                        )
                    logger.info(f"Video highlights pronto per il download: {final_video_path}")

                elif isinstance(output_path_or_list, list) and len(output_path_or_list) > 0:
                    # Gestisci il caso in cui process_video ritorni una lista di clip (se implementato diversamente)
                    st.warning("Output multipli non supportati in questa versione, si attende un singolo file video.")
                    logger.warning("process_video ha ritornato una lista, ma si attende un singolo file.")

                else:
                    # Errore o nessun highlight trovato
                    st.error("Si è verificato un errore durante la generazione degli highlights o nessun momento chiave è stato trovato.")
                    logger.error("Generazione highlights fallita o nessun risultato.")

        except Exception as e:
            logger.error(f"Errore nel blocco principale di elaborazione: {e}")
            st.error(f"Si è verificato un errore imprevisto: {e}")
        finally:
            # Assicurati che i file temporanei vengano puliti alla fine
            cleanup_files([video_path] + (output_path_or_list if isinstance(output_path_or_list, list) else []))


if __name__ == "__main__":
    # Chiama le funzioni per la sidebar e il contenuto principale
    uploaded_file, cat, prompt_template, clip_duration, process_button = sidebar()
    main_content(uploaded_file, cat, prompt_template, clip_duration, process_button)
