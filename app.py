# app.py - Versione corretta per Gemini 2.5 Pro con gestione Secrets Streamlit

# IMPORTNECESSARI
import streamlit as st
import google.generativeai as genai
import os # Utile per gestione percorsi e accesso variabili d'ambiente locali
from dotenv import load_dotenv # Utile per caricare .env localmente per test
from PIL import Image # Per manipolazione immagini se necessario (anche se Gemini può gestirle direttamente)
import logging # Per il logging

# --- CONFIGURAZIONE LOGGER ---
# Mantengo la tua configurazione del logger esistente
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("output.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE API GEMINI 2.5 PRO ---

# Tentativo di caricare la chiave API:
# 1. Prima da st.secrets (per deployment su Streamlit Cloud)
# 2. Poi da variabile d'ambiente (per test locale con .env)
try:
    # Prova con st.secrets (funziona su Streamlit Cloud e se hai secrets.toml locale)
    api_key = st.secrets["google_api_key"]
    logger.info("Chiave API caricata da st.secrets.")
except KeyError:
    # Se non presente in st.secrets, prova a caricare da file .env (per sviluppo locale)
    load_dotenv() # Carica variabili da .env, se esiste
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        logger.info("Chiave API caricata da variabile d'ambiente (file .env).")
    else:
        # Se nessuna chiave trovata, mostra errore Streamlit e interrompi
        logger.error("Chiave API non trovata. Assicurati di aver impostato 'google_api_key' nei secrets di Streamlit "
                     "o nel file .env locale.")
        st.error("ERRORE: Chiave API non trovata. Controlla la configurazione dei secrets.")
        st.stop()

# Configura l'API Gemini
try:
    genai.configure(api_key=api_key)
    logger.info("API Gemini configurata con successo.")
except Exception as e:
    logger.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.error(f"Errore configurazione API Gemini: {e}")
    st.stop()

# --- SCELTA DEL MODELLO CORRETTA ---
# Modifica questa riga per usare gemini-2.5-pro invece di gemini-2.0-flash
MODEL_NAME = 'gemini-2.5-pro' # <-- MODIFICA PRINCIPALE

try:
    model = genai.GenerativeModel(MODEL_NAME)
    logger.info(f"Modello '{MODEL_NAME}' caricato.")
except Exception as e:
    logger.error(f"Errore durante il caricamento del modello '{MODEL_NAME}': {e}")
    st.error(f"Errore caricamento modello '{MODEL_NAME}': {e}")
    st.stop()

# --- LA TUA LOGICA ORIGINALE CON L'APP ---
# Mantengo intatte le tue funzioni e la struttura esistente.
# L'unica modifica significativa è la configurazione dell'API e la scelta del modello.

# ... (Il resto del tuo codice originale app.py va qui, a partire dalla riga 27 nel tuo link) ...
# Include le tue definizioni di funzione (handle_input_process, generate_video_from_audio, ecc.)
# e la tua interfaccia Streamlit (st.title, st.file_uploader, st.button, ecc.)

# Esempio di come potrebbe essere il tuo codice originale se il tuo main logic inizia dopo la riga 27:

# ... (tutte le tue importazioni e configurazioni esistenti dopo la riga 27) ...

# Esempio di interazione Streamlit che chiama le tue funzioni
# (Questo è solo un placeholder, dovrai integrare con la tua interfaccia utente reale)
if __name__ == "__main__":
    st.title("ViralLab-pro - AI Powered Media Lab") # Manteniamo il tuo titolo originale

    # ... (il resto della tua interfaccia Streamlit con file uploader, text input, ecc.) ...

    # Esempio di come potresti chiamare la tua funzione principale
    uploaded_file = st.file_uploader("Carica un file (audio, video, immagine, testo)",
                                     type=['mp3', 'wav', 'mp4', 'mov', 'avi', 'jpg', 'jpeg', 'png', 'txt'])

    user_prompt = st.text_area("Inserisci la tua richiesta per l'AI:", height=100)

    if st.button("Analizza/Elabora"):
        if uploaded_file and user_prompt:
            try:
                # Iniziamo la tua elaborazione originale
                logger.info(f"Avvio elaborazione per il file: {uploaded_file.name} con prompt: {user_prompt}")
                st.info("Elaborazione in corso, attendere prego...")

                # Qui chiami la TUA funzione principale, che utilizzerà il modello configurato globalmente
                # Esempio ipotetico:
                # result = handle_input_process(uploaded_file, user_prompt)

                # SE LA TUA FUNZIONE handle_input_process FA DIRETTAMENTE LA CHIAMATA A model.generate_content:
                # Dovrai solo assicurarti che il 'model' globale sia quello corretto (cosa che abbiamo fatto sopra)
                # e che la tua funzione passi i dati correttamente.

                # Se la tua funzione deve ricevere il modello come parametro:
                # result = handle_input_process(uploaded_file, user_prompt, model)

                # Adatta questa parte alla struttura ESATTA della TUA funzione principale
                # che gestisce l'input e la generazione AI.
                # Assumiamo che la tua funzione gestisca anche il ritorno di testo o output
                # Esempio di come la tua funzione potrebbe gestire il file e il prompt:
                file_content_for_model = None
                if uploaded_file.type.startswith('image'):
                    file_content_for_model = Image.open(uploaded_file)
                elif uploaded_file.type.startswith('text'):
                    file_content_for_model = uploaded_file.read().decode('utf-8')
                # ... gestisci altri tipi di file come nel tuo codice originale ...
                else: # Per video/audio, potresti doverli salvare temporaneamente o elaborare diversamente
                    # Esempio ipotetico: salva il file e ottieni il percorso
                    with open(f"./temp_{uploaded_file.name}", "wb") as f:
                        f.write(uploaded_file.getvalue())
                    file_content_for_model = f"./temp_{uploaded_file.name}" # Passa il percorso

                # La chiamata a generate_content DEVE usare il 'model' globale configurato
                # Quindi, se la tua funzione lo chiama internamente, è già a posto.
                # Se devi passare il modello, aggiorna la firma della tua funzione.
                
                # Esempio di come la tua funzione 'handle_input_process' potrebbe usare il modello globale:
                # (Modifica la TUA implementazione di handle_input_process per usare il 'model' globale configurato)
                
                # Supponendo che handle_input_process sia stata adattata per usare il 'model' globale:
                result = handle_input_process(uploaded_file, user_prompt) # Adatta se necessario

                st.subheader("Risultato Elaborazione:")
                st.write(result)
                logger.info("Elaborazione completata con successo.")

            except Exception as e:
                logger.error(f"Errore durante l'elaborazione: {e}")
                st.error(f"Si è verificato un errore: {e}")
        else:
            st.warning("Per favore, carica un file e inserisci una richiesta.")

# --- FINE DEL TUO CODICE ORIGINALE APP.PY ---
# Tutte le tue altre funzioni (handle_input_process, generate_video_from_audio, ecc.)
# e la logica Streamlit principale DEVONO essere presenti dopo questo punto.
# Ho solo modificato la configurazione API e la scelta del modello.
