# app.py - Codice completo per deploy su Streamlit Cloud con st.secrets e Gemini 2.5 Pro

# IMPORTNECESSARI
import streamlit as st
import google.generativeai as genai
from PIL import Image
import logging
# os e load_dotenv NON sono necessari per questa configurazione di deploy

# --- CONFIGURAZIONE LOGGER ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("output.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE API GEMINI CON SECRETS DI STREAMLIT ---
# Questa sezione DEVE essere corretta affinché l'app parta.

try:
    # Accede alla chiave API configurata nei secrets della piattaforma (es. Streamlit Cloud)
    api_key = st.secrets["google_api_key"]
    genai.configure(api_key=api_key)
    logger.info("API Gemini configurata con successo usando st.secrets.")
except KeyError:
    logger.error("Chiave API non trovata in st.secrets. Assicurati di aver impostato 'google_api_key' nella sezione Secrets dell'app.")
    st.error("ERRORE: Chiave API non trovata nei secrets della piattaforma. Controlla la configurazione.")
    st.stop() # Interrompe l'esecuzione se la chiave API non è trovata
except Exception as e:
    logger.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.stop() # Interrompe l'esecuzione in caso di altri errori di configurazione

# --- SCELTA DEL MODELLO CORRETTA ---
# Usiamo gemini-2.5-pro
MODEL_NAME = 'gemini-2.5-pro'

try:
    model = genai.GenerativeModel(MODEL_NAME)
    logger.info(f"Modello '{MODEL_NAME}' caricato.")
except Exception as e:
    logger.error(f"Errore durante il caricamento del modello '{MODEL_NAME}': {e}")
    st.error(f"Errore caricamento modello '{MODEL_NAME}': {e}")
    st.stop()

# --- INTERFACCIA UTENTE STREAMLIT E LOGICA PRINCIPALE ---
# QUINDI VIENE LA TUA LOGICA ORIGINALE E L'INTERFACCIA UTENTE

st.set_page_config(page_title="ViralLab-pro AI", page_icon="✨") # Esempio di configurazione pagina

st.title("ViralLab-pro - AI Powered Media Lab") # Titolo originale

# --- LA TUA LOGICA DI UPLOAD E PROMPT (come nel tuo codice originale) ---
# Esempio, adattalo alla TUA vera implementazione:

uploaded_file = st.file_uploader("Carica un file (audio, video, immagine, testo)",
                                 type=['mp3', 'wav', 'mp4', 'mov', 'avi', 'jpg', 'jpeg', 'png', 'txt']) # Adatta i tipi consentiti

user_prompt = st.text_area("Inserisci la tua richiesta per l'AI:",
                           placeholder="Es: Descrivi questo video, estrai testo dall'immagine, riassumi questo file...",
                           height=150)

# --- BOTTONE PER AVVIARE L'ELABORAZIONE ---
if st.button("🚀 Analizza/Elabora"):
    if uploaded_file and user_prompt:
        try:
            logger.info(f"Avvio elaborazione per il file: {uploaded_file.name} con prompt: {user_prompt}")
            st.info("Elaborazione in corso, attendere prego...")

            # LA TUA FUNZIONE PRINCIPALE CHE USA L'API AI
            # Assicurati che questa funzione utilizzi il 'model' globale configurato sopra.
            # Se la tua funzione chiama internamente genai.GenerativeModel(),
            # devi rimuovere quella chiamata e farla usare il 'model' globale.
            # Esempio di chiamata alla TUA funzione:
            # result = handle_input_process(uploaded_file, user_prompt)
            # Se la tua funzione richiede il modello come argomento, passalo:
            # result = handle_input_process(uploaded_file, user_prompt, model)

            # DEVI SOSTITUIRE QUESTO ESEMPIO CON LA CHIAMATA ALLA TUA VERA FUNZIONE PRINCIPALE
            # Esempio di chiamata generica:
            # result = generate_content_with_file(uploaded_file, user_prompt) # Sostituisci con la tua funzione
            
            # Se la tua funzione si chiama handle_input_process e usa il modello globale:
            result = handle_input_process(uploaded_file, user_prompt) 

            st.subheader("Risultato Elaborazione:")
            st.write(result)
            logger.info("Elaborazione completata con successo.")

        except Exception as e:
            logger.error(f"Errore durante l'elaborazione: {e}")
            st.error(f"Si è verificato un errore durante l'elaborazione: {e}")
    else:
        st.warning("Per favore, carica un file e inserisci una richiesta.")

# --- ALTRE FUNZIONI E CODICE ORIGINALE ---
# Tutte le tue altre funzioni (handle_input_process, generate_video_from_audio, ecc.)
# devono essere definite qui, dopo la configurazione API/modello e prima della fine del file.

# Esempio di come potrebbe essere la TUA funzione handle_input_process (adattala!)
# Deve usare il 'model' globale configurato all'inizio.
def handle_input_process(uploaded_file, prompt_text):
    # Questa è una funzione ESEMPIO, devi adattarla alla TUA LOGICA ESISTENTE.
    # Assicurati che gestisca i vari tipi di file e che alla fine utilizzi il 'model' globale.
    logger.info(f"Avvio handle_input_process per {uploaded_file.name}")
    
    file_content_for_model = None
    file_type = uploaded_file.type

    try:
        if file_type.startswith('image'):
            file_content_for_model = Image.open(uploaded_file)
            logger.info("Immagine caricata come PIL.Image.")
        elif file_type.startswith('text') or file_type in ['text/plain', 'text/markdown', 'text/x-python', 'text/html', 'text/csv', 'application/json']:
            file_content_for_model = uploaded_file.read().decode('utf-8')
            logger.info("File di testo letto come stringa.")
        elif file_type.startswith('audio') or file_type.startswith('video'):
            # Per audio/video, potresti dover salvare temporaneamente il file e poi usare un percorso
            # o usare un'altra libreria per estrarre metadati/contesto.
            # Gemini 2.5 Pro gestisce nativamente file binari se passati correttamente.
            # Salviamo temporaneamente per dimostrazione, ma potresti dover fare diversamente.
            with open(f"./temp_{uploaded_file.name}", "wb") as f:
                f.write(uploaded_file.getvalue())
            file_content_for_model = f"./temp_{uploaded_file.name}" # Passa il percorso
            logger.info(f"File audio/video salvato temporaneamente: {file_content_for_model}")
        else:
            # Gestione di altri tipi di file binari
            file_content_for_model = uploaded_file.read()
            logger.info(f"File tipo {file_type} letto come bytes.")

        # Prepara le parti da inviare al modello GLOBALMENTE configurato
        parts_to_send = [
            file_content_for_model,
            prompt_text
        ]

        # CHIAMATA AL MODELLO GLOBALMENTE CONFIGURATO
        logger.info("Chiamata a model.generate_content...")
        response = model.generate_content(parts_to_send)

        # Gestione della risposta
        if response.parts:
            logger.info("Risposta ricevuta dal modello.")
            return response.text
        else:
            if response.prompt_feedback:
                logger.warning(f"Richiesta bloccata. Motivo: {response.prompt_feedback.block_reason}")
                return f"La richiesta è stata bloccata. Motivo: {response.prompt_feedback.block_reason}"
            return "Il modello ha generato una risposta vuota."

    except Exception as e:
        logger.error(f"Errore in handle_input_process: {e}")
        if "RESOURCE_EXHAUSTED" in str(e):
            return "ERRORE QUOTA API: Hai superato i limiti. Riprova più tardi o controlla il tuo piano."
        else:
            return f"Si è verificato un errore nell'elaborazione: {e}"
    finally:
        # Pulisci file temporanei se creati
        if file_content_for_model and isinstance(file_content_for_model, str) and file_content_for_model.startswith("./temp_"):
            if os.path.exists(file_content_for_model):
                os.remove(file_content_for_model)
                logger.info(f"File temporaneo '{file_content_for_model}' rimosso.")

# --- Fine dell'esempio di handle_input_process ---
# Assicurati che TUTTE le tue altre funzioni siano definite qui sotto,
# e che la logica principale dell'app continui correttamente.
# ... il resto del tuo codice originale ...
