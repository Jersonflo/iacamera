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
        with sr.Microphone(device_index=0) as source:
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
                        
                        # Mantener el hilo de conversación
                        while True:
                            try:
                                print("Esperando una pregunta o palabra de cierre...")
                                pregunta_audio = self.reconocedor.listen(source, timeout=100)
                                pregunta_texto = self.reconocedor.recognize_google(pregunta_audio, language=self.language).lower()
                                print(f"Pregunta escuchada: {pregunta_texto}")

                                # Detectar palabra clave de cierre
                                if pregunta_texto.strip() == "terminar":
                                    mensaje_cierre = "Gracias por hablar conmigo. ¡Adiós!"
                                    print(mensaje_cierre)
                                    self.reproducir_respuesta(mensaje_cierre)
                                    break

                                # Verificar si el texto es una pregunta válida
                                if self.es_pregunta(pregunta_texto):
                                    respuesta = self.chatbot_app.enviar_mensaje(pregunta_texto)
                                    print(f"Respuesta del ChatBot: {respuesta}")
                                    self.reproducir_respuesta(respuesta)
                                else:
                                    mensaje_error = "Parece que no has hecho una pregunta. Por favor, intenta nuevamente."
                                    print(mensaje_error)
                                    self.reproducir_respuesta(mensaje_error)

                            except sr.UnknownValueError:
                                print("No entendí lo que dijiste. Intenta de nuevo.")
                            except sr.RequestError:
                                print("Error con el servicio de reconocimiento de voz. Terminando conversación.")
                                break

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

    def es_pregunta(self, texto):
        """Verifica si el texto ingresado es una pregunta."""
        palabras_pregunta = [
        # Interrogativos comunes
        "qué", "cuál", "cómo", "cuándo", "dónde", "por qué", "quién", "quiénes", 
        "para qué", "de qué", "por cuánto", "en qué", "con qué", "hasta cuándo",
    
        # Verbos y auxiliares comunes en preguntas
        "es", "puedo", "puedes", "podrías", "pueden", "hay", "tiene", "tienen", 
        "está", "están", "sería", "serían", "debería", "deberían", "necesito", 
        "quiero", "querría", "querrías", "podría", "debo", "debes", "sabías", 
        "sabes", "entiendes", "entiende", "entienden", "conoces", "conocen", 
        "conocerías", "explicas", "explicaría", "dices", "dirías", "pueda", "quiere",

        # Expresiones contextuales
        "me podrías", "te gustaría", "será posible", "puede ser", "es cierto", 
        "es verdad", "me dices", "te importa", "sabes si", "me puedes decir", 
        "alguien sabe", "me ayudas", "puedes ayudarme", "qué tal si", "hay manera",
        "cuánto cuesta", "cuánto tiempo", "cómo puedo", "cómo se hace", 
        "qué opinas", "qué significa", "qué pasa", "qué ocurre", 

        # Formas coloquiales y modismos
        "qué onda", "qué rollo", "qué hay", "qué fue", "qué pedo", "cómo va", 
        "cómo ves", "qué te parece", "qué onda contigo", "qué onda con", 
        "qué rayos", "qué demonios", "qué carajos",

        # Preguntas implícitas
        "quisiera saber", "me gustaría saber", "podrías explicarme", 
        "necesitaría saber", "podrías decirme", "quisieras ayudarme", 
        "serías tan amable de", "me interesa saber", "te pregunto si", 
        "tendrías idea", "tienes idea", "puedes decirme", "puedes explicarme", 
        "te pregunto", "quisiera preguntar", "hay alguna forma de"
    ]
        return "?" in texto or any(texto.startswith(p) for p in palabras_pregunta)

    def detener_escucha(self):
        """Detiene la escucha continua."""
        self.escuchando = False
