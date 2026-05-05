import time # Assicurati che ci sia questo import in cima al file

# ... (resto del codice sopra invariato)

            # AI AGENT SPECIALIZZATO
            model = genai.GenerativeModel('gemini-1.5-flash')
            video_ai = genai.upload_file(path=path)
            
            # --- AGGIUNTA: ATTESA ELABORAZIONE VIDEO ---
            status.update(label="Google sta elaborando il video...", state="running")
            while video_ai.state.name == "PROCESSING":
                time.sleep(2)
                video_ai = genai.get_file(video_ai.name)
            
            if video_ai.state.name == "FAILED":
                st.error("Errore nell'elaborazione del video su Google AI.")
                st.stop()
            # --------------------------------------------

            # Ora l'AI può procedere
            prompt = f"""
            Sei un esperto Viral Strategist per {category}.
            Ottimizza questo contenuto per {platform} ({content_type}).
            ...
