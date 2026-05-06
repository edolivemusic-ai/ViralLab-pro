# 🎬 Puglia Sizzle Lab: Highlight Editor

Una web app per creare montaggi video virali con l'aiuto di AI Gemini, specializzata per contenuti Puglia.

## 🚀 Installazione Locale

1. Clona il repository
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura la API key:
   - Copia `.streamlit/secrets.toml.example` in `.streamlit/secrets.toml`
   - Inserisci la tua Gemini API key
4. Avvia l'app:
   ```bash
   streamlit run app.py
   ```

## 🔧 Deploy su Streamlit Cloud

1. Carica i file su GitHub
2. Su Streamlit Cloud, collega il repository
3. Nel pannello Secrets, aggiungi:
   ```
   GEMINI_API_KEY = tua_api_key
   ```

## 📋 Funzionalità

- Analisi AI dei video per trovare momenti di picco energetico
- Elaborazione audio-driven per ritrovare i momenti migliori
- Supporto per Instagram, TikTok, Facebook
- Watermark personalizzabile
- Colonna sonora personalizzata
- Processing parallelo per analisi veloce

## 🎯 Piattaforme Supportate

- **Instagram**: Reels (90s), Storie (60s), Post (60s)
- **TikTok**: Reels (180s), Storie (60s), Post (180s)  
- **Facebook**: Reels (60s), Storie (20s), Post (240s)

## ⚠️ Note Importanti

- Dimensione massima file: 500MB
- Massimo 10 clip per sessione
- Formati supportati: MP4, MOV
- Audio colonna sonora: MP3, WAV, AAC, M4A

## 🐛 Risoluzione Problemi

Se riscontri problemi:
1. Verifica che la API key sia configurata correttamente
2. Controlla che i file video siano in formato supportato
3. Assicurati di avere abbastanza RAM per il processing video
4. Su Streamlit Cloud, controlla i limiti di risorse

## 📄 Licenza

MIT License
