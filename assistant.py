import os
import threading
import queue
import time
import tempfile
import asyncio
import speech_recognition as sr
import vertexai
from vertexai.generative_models import GenerativeModel
import edge_tts
import pygame

class VoiceAssistant:
    def __init__(self, api_key=None):
        # Para Vertex AI con ADC local, se inicializa usando vertexai.init
        # El Project ID se autodetecta desde la credencial ADC
        try:
            vertexai.init(project="gen-lang-client-0510406036", location="us-central1")
            # Cambiamos a 'gemini-1.5-flash' para evitar el error de modalidad de audio
            self.model = GenerativeModel('gemini-2.5-pro')
            print("[Asistente] Inicializado correctamente con Vertex AI.")
        except Exception as e:
            print(f"[Asistente] Error al inicializar Vertex AI: {e}")
            self.model = None

        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        # Opciones de audio
        pygame.mixer.init()
        
        # Estado
        self.is_running = False
        self.is_speaking = False
        
        # Callbacks (deben ser configurados por la UI)
        self.on_state_change = None      # (estado: str)
        self.on_user_text = None         # (texto: str)
        self.on_bot_response = None      # (texto: str)
        
        # Hilo de procesamiento
        self.thread = None

    def start(self):
        if self.is_running:
            return
        
        if not self.model:
            if self.on_state_change:
                self.on_state_change("Error: Modelo de Vertex AI no inicializado")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        self.stop_speaking()
        if self.on_state_change:
            self.on_state_change("Detenido")

    def stop_speaking(self):
        """Interrumpe el audio actual."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.is_speaking = False

    def _run_loop(self):
        """Bucle principal en segundo plano."""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
        while self.is_running:
            # Si está hablando, no escuchamos para evitar eco
            if self.is_speaking:
                time.sleep(0.1)
                continue

            if self.on_state_change:
                self.on_state_change("Escuchando...")
                
            try:
                # Listen in short chunks to remain responsive to "stop"
                with self.mic as source:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=10)
                
                # Si dejó de correr mientras escuchaba
                if not self.is_running:
                    break
                    
                if self.on_state_change:
                    self.on_state_change("Procesando audio...")
                
                text = self.recognizer.recognize_google(audio, language="es-MX")
                if text:
                    if self.on_user_text:
                        self.on_user_text(text)
                    self._process_and_respond(text)
                    
            except sr.WaitTimeoutError:
                pass # Silencio, seguir escuchando
            except sr.UnknownValueError:
                pass # No se entendió, ignorar
            except Exception as e:
                print(f"[Asistente] Error: {e}")
                time.sleep(1)

    def _process_and_respond(self, user_text):
        """Consulta a Gemini y genera TTS."""
        if not self.is_running: return
        
        if self.on_state_change:
            self.on_state_change("Pensando...")
            
        try:
            # Prompt optimizado para respuestas cortas y conversacionales
            prompt = f"Responde de forma breve, concisa y amigable (máximo 2-3 oraciones). Usuario: {user_text}"
            response = self.model.generate_content(prompt)
            bot_text = response.text.strip()
            
            if self.on_bot_response:
                self.on_bot_response(bot_text)
                
            self._speak(bot_text)
            
        except Exception as e:
            print(f"[Gemini] Error: {e}")
            if self.on_state_change:
                self.on_state_change("Error de conexión.")

    def _speak(self, text):
        """Genera el TTS y lo reproduce de forma no bloqueante."""
        if not self.is_running: return
        self.is_speaking = True
        
        if self.on_state_change:
            self.on_state_change("Hablando...")
            
        # Para usar edge-tts de forma asíncrona dentro de un hilo síncrono
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()

        try:
            communicate = edge_tts.Communicate(text, "es-MX-DaliaNeural")
            asyncio.run(communicate.save(temp_path))
            
            # Reproducir con pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Esperar a que termine de reproducir, pero permitir interrupción
            while pygame.mixer.music.get_busy() and self.is_running and self.is_speaking:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            self.is_speaking = False
            # Limpiar archivo temp
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
