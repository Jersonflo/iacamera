import speech_recognition as sr

class SpeechRecognizer:
    def __init__(self, language="es-ES"):
        # Inicializa el reconocedor y establece el idioma
        self.reconocedor = sr.Recognizer()
        self.language = language

    def ajustar_ruido_ambiental(self, source):
        """Ajusta el ruido ambiental para mejorar el reconocimiento."""
        self.reconocedor.adjust_for_ambient_noise(source)

    def escuchar(self):
        """Utiliza el micrófono para escuchar y convertir audio a texto."""
        with sr.Microphone() as source:
            print("Di algo...")
            # Ajusta el ruido ambiental antes de escuchar
            self.ajustar_ruido_ambiental(source)
            audio = self.reconocedor.listen(source)
            return audio

    def reconocer(self, audio):
        """Convierte el audio en texto."""
        try:
            texto = self.reconocedor.recognize_google(audio, language=self.language)
            print("Has dicho: " + texto)
            return texto
        except sr.UnknownValueError:
            print("No se pudo entender el audio.")
            return None
        except sr.RequestError:
            print("No se pudo obtener resultados del servicio de reconocimiento de voz.")
            return None

# Ejemplo de uso
if __name__ == "__main__":
    reconocedor = SpeechRecognizer()
    audio = reconocedor.escuchar()
    texto = reconocedor.reconocer(audio)
