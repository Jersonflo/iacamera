import speech_recognition as sr
import threading

class SpeechRecognizer:
    def __init__(self, language="es-ES", keyword="activa"):
        # Inicializa el reconocedor y establece el idioma y la palabra clave
        self.reconocedor = sr.Recognizer()
        self.language = language
        self.keyword = keyword
        self.escuchando = False

    def ajustar_ruido_ambiental(self, source):
        """Ajusta el ruido ambiental para mejorar el reconocimiento."""
        self.reconocedor.adjust_for_ambient_noise(source)

    def escuchar_continuamente(self, on_keyword_detected):
        """Escucha continuamente y activa el reconocimiento cuando se detecta la palabra clave."""
        self.escuchando = True
        with sr.Microphone() as source:
            print("Escuchando continuamente...")
            self.ajustar_ruido_ambiental(source)
            while self.escuchando:
                try:
                    audio = self.reconocedor.listen(source, timeout=5)
                    texto = self.reconocedor.recognize_google(audio, language=self.language).lower()
                    print(f"Escuchado: {texto}")
                    if self.keyword in texto:
                        print(f"Palabra clave '{self.keyword}' detectada. Activando reconocimiento de voz...")
                        on_keyword_detected()
                except sr.UnknownValueError:
                    pass  # Ignorar si el audio no es comprensible
                except sr.RequestError:
                    print("Error con el servicio de reconocimiento de voz.")
                    self.escuchando = False  # Detener si hay un problema de conexión

    def detener_escucha(self):
        """Detiene la escucha continua."""
        self.escuchando = False
