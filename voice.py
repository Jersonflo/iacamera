import speech_recognition as sr
import threading
import queue


class SpeechRecognizer:
    def __init__(self, language="es-ES", keyword="juan"):
        # Inicializa el reconocedor y establece el idioma y la palabra clave
        self.reconocedor = sr.Recognizer()
        self.language = language
        self.keyword = keyword.lower()
        self.escuchando = True
        self.q = queue.Queue()  # Cola para almacenar las preguntas detectadas

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
                    audio = self.reconocedor.listen(source, timeout=8)
                    texto = self.reconocedor.recognize_google(audio, language=self.language).lower()
                    print(f"Escuchado: {texto}")
                
                    # Activar solo si se dice la palabra clave exacta
                    if texto.strip() == self.keyword:
                        print(f"Palabra clave '{self.keyword}' detectada. Haz tu pregunta.")
                    
                        # Escucha otra vez para capturar la pregunta completa
                        pregunta_audio = self.reconocedor.listen(source, timeout=5)
                        pregunta_texto = self.reconocedor.recognize_google(pregunta_audio, language=self.language).lower()
                        #print(f"Pregunta capturada: {pregunta_texto}")
                        return pregunta_texto
                        # enviamos la pregunta en la cola
                        self.q.put(pregunta_texto)  
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    print("Error con el servicio de reconocimiento de voz.")
                    break


    def detener_escucha(self):
        """Detiene la escucha continua."""
        self.escuchando = False
