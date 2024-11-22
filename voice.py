import speech_recognition as sr
from Gemini import ChatBotApp
import pyttsx3
import queue
import csv


class SpeechRecognizer:
    def __init__(self, language="es-ES", keyword="iniciar", q=None):
        self.reconocedor = sr.Recognizer()
        self.language = language
        self.keyword = keyword.lower()
        self.escuchando = True
        self.q = q if q is not None else queue.Queue()  # Usa la cola externa si se proporciona
        self.chatbot_app = ChatBotApp()
        self.engine = pyttsx3.init()
        self.persona_id = 0  # Identificador para cada persona
        self.csv_file = "preguntas_respuestas.csv"
        self.campos = ["Persona", "Pregunta", "Respuesta"]
        # Inicializar el archivo CSV si no existe
        self.inicializar_csv()

    def inicializar_csv(self):
        """Inicializa el archivo CSV con encabezados si no existe."""
        try:
            with open(self.csv_file, mode="x", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.campos)
                writer.writeheader()
        except FileExistsError:
            pass  # Si el archivo ya existe, no hace nada

    def ajustar_ruido_ambiental(self, source):
        """Ajusta el ruido ambiental para mejorar el reconocimiento."""
        self.reconocedor.adjust_for_ambient_noise(source)

    def guardar_en_csv(self, persona, pregunta, respuesta):
        """Guarda una entrada de pregunta-respuesta en el archivo CSV."""
        try:
            with open(self.csv_file, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.campos)
                writer.writerow({"Persona": persona, "Pregunta": pregunta, "Respuesta": respuesta})
        except Exception as e:
            print(f"Error al guardar en CSV: {e}")

    def reproducir_respuesta(self, respuesta):
        """Reproduce la respuesta del chatbot mediante voz."""
        self.engine.say(respuesta)
        self.engine.runAndWait()

    def escuchar_continuamente(self):
        """Escucha continuamente y procesa preguntas cuando se detecta la palabra clave."""
        with sr.Microphone(device_index=0) as source:
            print("Esperando la palabra clave...")
            self.ajustar_ruido_ambiental(source)

            while self.escuchando:
                try:
                    # Escuchar audio y convertir a texto
                    audio = self.reconocedor.listen(source, timeout=100)
                    texto = self.reconocedor.recognize_google(audio, language=self.language).lower()
                    print(f"Escuchado: {texto}")

                    if texto.strip() == self.keyword:
                        self.persona_id += 1  # Incrementa para una nueva persona
                        print(f"Palabra clave '{self.keyword}' detectada. Iniciando conversación.")
                        self.reproducir_respuesta("Hola, soy el Bot. ¿En qué puedo ayudarte?")

                        # Procesar preguntas de la conversación
                        while True:
                            try:
                                print("Esperando pregunta...")
                                pregunta_audio = self.reconocedor.listen(source, timeout=100)
                                pregunta_texto = self.reconocedor.recognize_google(pregunta_audio, language=self.language).lower()
                                print(f"Pregunta escuchada: {pregunta_texto}")

                                # Detectar cierre de conversación
                                if pregunta_texto.strip() == "terminar":
                                    self.reproducir_respuesta("Gracias por hablar conmigo. ¡Adiós!")
                                    print("Conversación terminada.")
                                    break

                                # Obtener respuesta del chatbot
                                respuesta = self.chatbot_app.enviar_mensaje(pregunta_texto)
                                print(f"Respuesta del ChatBot: {respuesta}")
                                self.reproducir_respuesta(respuesta)

                                # Guardar en CSV
                                self.guardar_en_csv(
                                    persona=f"Persona {self.persona_id}",
                                    pregunta=pregunta_texto,
                                    respuesta=respuesta,
                                )
                            except sr.UnknownValueError:
                                print("No entendí lo que dijiste. Intenta de nuevo.")
                            except sr.RequestError as e:
                                print(f"Error con el reconocimiento de voz: {e}. Terminando conversación.")
                                break
                except sr.UnknownValueError:
                    pass  # Ignorar si no se entiende
                except sr.RequestError as e:
                    print(f"Error con el reconocimiento de voz: {e}")
                    break
