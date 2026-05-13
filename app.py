# app.py

import streamlit as st
import google.generativeai as genai
from PIL import Image
import os # Utile per gestione percorsi, se necessario

# --- CONFIGURAZIONE API GEMINI 2.5 PRO ---

# Utilizza st.secrets per la chiave API, ideale per Streamlit Cloud
# Se stai testando localmente, assicurati di avere un file secrets.toml nella stessa directory
# con il contenuto:
# [secrets]
# google_api_key = "LA_TUA_CHIAVE_API_OTENUTA_DA_AI_STUDIO"
try:
    api_key = st.secrets["google_api_key"]
    genai.configure(api_key=api_key)
    # In un'app reale, eviterei i print() in produzione, ma per debug va bene
    # print("API Gemini configurata con successo tramite secrets.")
except KeyError:
    st.error("ERRORE: Chiave API non trovata nei secrets di Streamlit. "
             "Assicurati di aver impostato 'google_api_key' nella sezione secrets dell'app "
             "(es. nel file secrets.toml locale o nelle impostazioni del tuo deploy).")
    st.stop() # Interrompe l'esecuzione dell'app Streamlit
except Exception as e:
    st.error(f"Errore durante la configurazione dell'API Gemini: {e}")
    st.stop()

# --- SCELTA DEL MODELLO ---
# Usiamo gemini-2.5-pro per la sua potenza e ampia finestra di contesto.
# 'gemini-2.5-flash' è un'alternativa più veloce e a basso costo, se necessario.
MODEL_NAME = 'gemini-2.5-pro'

try:
    model = genai.GenerativeModel(MODEL_NAME)
    # print(f"Modello '{MODEL_NAME}' caricato.")
except Exception as e:
    st.error(f"Errore durante il caricamento del modello '{MODEL_NAME}': {e}")
    st.stop()

# --- FUNZIONE PER ANALISI FILE E GENERAZIONE CONTENUTO CON GEMINI ---

def analyze_file_with_gemini(uploaded_file, prompt_text: str):
    """
    Analizza un file caricato tramite Streamlit e genera una risposta usando Gemini.

    Args:
        uploaded_file: L'oggetto file caricato da st.file_uploader.
        prompt_text (str): Il testo della domanda o istruzione per il modello.

    Returns:
        str: La risposta del modello, o un messaggio di errore.
    """
    if uploaded_file is None:
        return "Errore: Nessun file caricato."
    if not prompt_text:
        return "Errore: Il prompt non può essere vuoto."

    try:
        file_content = None
        # Determina il tipo di file e leggi il contenuto appropriato
        if uploaded_file.type.startswith('image'):
            img = Image.open(uploaded_file)
            file_content = img
            st.write(f"File immagine caricato: {uploaded_file.name} ({uploaded_file.type})")
        elif uploaded_file.type in ['text/plain', 'text/markdown', 'text/x-python', 'text/html', 'text/csv']:
            # Legge il contenuto come testo UTF-8
            file_content = uploaded_file.read().decode('utf-8')
            st.write(f"File di testo caricato: {uploaded_file.name} ({uploaded_file.type})")
        else:
            # Per altri tipi di file binari, leggi come bytes.
            # Potrebbe essere necessario adattare il prompt o il modello se si aspettano dati specifici.
            file_content = uploaded_file.read()
            st.write(f"File caricato: {uploaded_file.name} ({uploaded_file.type}) - Gestito come dati generici.")

        # Prepara le parti da inviare al modello: il contenuto del file e il prompt
        parts_to_send = [
            file_content,
            prompt_text
        ]

        # Invia la richiesta al modello Gemini
        st.write("Invio della richiesta al modello Gemini 2.5 Pro...")
        response = model.generate_content(parts_to_send)

        # Verifica la risposta
        if response.parts:
            return response.text
        else:
            # Controlla se la risposta è stata bloccata per motivi di sicurezza/policy
            if response.prompt_feedback:
                return f"La richiesta è stata bloccata dal modello. Motivo: {response.prompt_feedback.block_reason}. Dettagli: {response.prompt_feedback.safety_ratings}"
            return "Il modello ha generato una risposta vuota."

    except Exception as e:
        # Gestisce specificamente l'errore di esaurimento quote
        if "RESOURCE_EXHAUSTED" in str(e):
            # Stampa un messaggio più leggibile per l'utente in Streamlit
            st.error("ERRORE QUOTA: Hai superato i limiti di utilizzo dell'API. "
                     "Riprova più tardi o considera l'aggiornamento del tuo piano. "
                     "Dettagli: RESOURCE_EXHAUSTED.")
            return f"Errore di quota: {e}" # Potrebbe essere utile per il log backend
        else:
            st.error(f"Si è verificato un errore imprevisto durante l'analisi: {e}")
            return f"Errore generico: {e}"

# --- INTERFACCIA UTENTE STREAMLIT ---

st.set_page_config(page_title="Analizzatore AI Multimodale", page_icon="✨")

st.title("✨ Analizzatore Multimodale con Gemini 2.5 Pro")
st.markdown("""
Carica un file (immagini, testo, documenti, ecc.) e fai una domanda al modello AI.
Gemini 2.5 Pro è pronto ad analizzare e rispondere!
""")

# Upload del file
uploaded_file = st.file_uploader("Carica un file",
                                 type=['jpg', 'jpeg', 'png', 'gif', 'bmp', # Immagini
                                       'txt', 'md', 'py', 'html', 'csv', 'json'], # Testi e codice
                                 help="Tipi di file supportati includono immagini, testo semplice, codice Python, HTML, CSV e JSON.")

# Input per il prompt dell'utente
user_prompt = st.text_area("Scrivi la tua domanda o istruzione qui:",
                           placeholder="Es: Descrivi questa immagine. / Riassumi questo testo. / Spiega questo codice.",
                           height=150)

# Bottone per avviare l'analisi
if st.button("🚀 Analizza File"):
    if uploaded_file is not None and user_prompt:
        # Mostra un messaggio di attesa mentre il modello elabora
        with st.spinner("L'AI sta analizzando il tuo file..."):
            # Chiama la funzione principale di analisi
            response_text = analyze_file_with_gemini(uploaded_file, user_prompt)

        st.subheader("Risposta del Modello:")
        # Mostra la risposta o un messaggio di errore
        if response_text.startswith("ERRORE:") or response_text.startswith("Errore"):
            st.error(response_text)
        else:
            st.write(response_text)
    elif uploaded_file is None:
        st.warning("⚠️ Per favore, carica un file prima di procedere.")
    else: # user_prompt è vuoto
        st.warning("⚠️ Per favore, inserisci una domanda o istruzione.")

st.markdown("---")
st.markdown("Powered by [Google Gemini 2.5 Pro](https://ai.google.dev/models/gemini) e [Streamlit](https://streamlit.io/)")
