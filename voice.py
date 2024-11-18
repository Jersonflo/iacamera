import speech_recognition as sr
from Gemini import ChatBotApp
import pyttsx3 
import queue


class SpeechRecognizer:
    def __init__(self, language="es-ES", keyword="iniciar", q=None):
        self.reconocedor = sr.Recognizer()
        self.language = language
        self.keyword = keyword.lower()
        self.escuchando = True
        self.q = q if q is not None else queue.Queue()  # Usa la cola externa si se proporciona
        self.chatbot_app = ChatBotApp() 
        self.engine = pyttsx3.init()
        
    def ajustar_ruido_ambiental(self, source):
        """Ajusta el ruido ambiental para mejorar el reconocimiento."""
        self.reconocedor.adjust_for_ambient_noise(source)

    def escuchar_continuamente(self):
        """Escucha continuamente y coloca la pregunta capturada en la cola cuando se detecta la palabra clave."""
        with sr.Microphone() as source:
            print("Esperando la palabra clave...")
            self.ajustar_ruido_ambiental(source)
        
            while self.escuchando:
                try:
                    # Escucha continuamente pero analiza solo si la palabra clave fue detectada
                    audio = self.reconocedor.listen(source, timeout=100)
                    texto = self.reconocedor.recognize_google(audio, language=self.language).lower()
                    print(f"Escuchado: {texto}")
                
                    # Activar solo si se dice la palabra clave exacta
                    if texto.strip() == self.keyword:
                        print(f"Palabra clave '{self.keyword}' detectada. Haz tu pregunta.")
                        
                        mensaje_saludo = "Hola, cómo estás, soy Bot, la mascota de Ecosystem, ¿en qué puedo ayudarte?"
                        self.reproducir_respuesta(mensaje_saludo)
                        # Escucha otra vez para capturar la pregunta completa
                        pregunta_audio = self.reconocedor.listen(source, timeout=5)
                        pregunta_texto = self.reconocedor.recognize_google(pregunta_audio, language=self.language).lower()
                        
                        respuesta = self.chatbot_app.enviar_mensaje(pregunta_texto)
                        print(f"Respuesta del ChatBot: {respuesta}")
                        self.reproducir_respuesta(respuesta)
                        
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    print("Error con el servicio de reconocimiento de voz.")
                    break
                
    def procesar_pregunta(self):
        """Procesa la pregunta de la cola y la pasa al chatbot para obtener una respuesta."""
        if not self.q.empty():
            pregunta = self.q.get_nowait()
            print(f"Pregunta capturada: {pregunta}")
            if pregunta:
                respuesta = self.chatbot_app.enviar_mensaje(pregunta)
                print(f"Respuesta del ChatBot: {respuesta}")
                self.reproducir_respuesta(respuesta)


    def reproducir_respuesta(self, respuesta):
        """Reproduce la respuesta del chatbot mediante voz."""
        self.engine.say(respuesta)
        self.engine.runAndWait()

    def detener_escucha(self):
        """Detiene la escucha continua."""
        self.escuchando = False
