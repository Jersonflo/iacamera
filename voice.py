import speech_recognition as sr
from Gemini import ChatBotApp
import matplotlib.pyplot as plt
import pyttsx3
import queue
import json
import numpy as np
import wave
import io


class SpeechRecognizer:
    def __init__(self, language="es-ES", keyword="iniciar", q=None):
        self.reconocedor = sr.Recognizer()
        self.language = language
        self.keyword = keyword.lower()
        self.escuchando = True
        self.q = q if q is not None else queue.Queue()
        self.chatbot_app = ChatBotApp()
        self.engine = pyttsx3.init()
        self.json_file = "preguntas_respuestas.json"
        self.inicializar_json()

    def inicializar_json(self):
        """Inicializa el archivo JSON si no existe."""
        try:
            with open(self.json_file, "x", encoding="utf-8") as file:
                json.dump([], file)  # Crear un archivo JSON vacío con una lista
        except FileExistsError:
            pass

    def ajustar_ruido_ambiental(self, source):
        """Ajusta el ruido ambiental para mejorar el reconocimiento."""
        self.reconocedor.adjust_for_ambient_noise(source)

    def guardar_en_json(self, persona, pregunta, respuesta, frecuencia):
        """Guarda una entrada de pregunta-respuesta en el archivo JSON."""
        try:
            # Leer el contenido actual del archivo JSON
            with open(self.json_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            # Agregar la nueva entrada
            nueva_entrada = {
                "Persona": persona,
                "Pregunta": pregunta,
                "Respuesta": respuesta,
                "Frecuencia": frecuencia,
            }
            data.append(nueva_entrada)

            # Escribir de vuelta al archivo JSON
            with open(self.json_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Error al guardar en JSON: {e}")

    def reproducir_respuesta(self, respuesta):
        """Reproduce la respuesta del chatbot mediante voz."""
        self.engine.say(respuesta)
        self.engine.runAndWait()

    def calcular_frecuencia_dominante(self, audio_data):
        """Calcula la frecuencia dominante en el audio."""
        with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            audio_frames = wav_file.readframes(n_frames)
            audio_samples = np.frombuffer(audio_frames, dtype=np.int16)

            # FFT para obtener frecuencias
            spectrum = np.fft.fft(audio_samples)
            freqs = np.fft.fftfreq(len(spectrum), d=1/framerate)

            # Filtrar frecuencias positivas
            positive_freqs = freqs[:len(freqs) // 2]
            positive_spectrum = np.abs(spectrum[:len(spectrum) // 2])

            # Encontrar la frecuencia dominante
            peak_freq = positive_freqs[np.argmax(positive_spectrum)]
            return peak_freq
        
        
        
    def graficar_espectro(self, audio_data):
        """
        Grafica el espectro de frecuencia y el nivel de decibeles en el tiempo.
        """
        try:
            with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                n_frames = wav_file.getnframes()
                framerate = wav_file.getframerate()
                audio_frames = wav_file.readframes(n_frames)
                audio_samples = np.frombuffer(audio_frames, dtype=np.int16)

                # Calcular el tiempo
                tiempo = np.linspace(0, len(audio_samples) / framerate, num=len(audio_samples))

                # FFT para espectro de frecuencia
                spectrum = np.fft.fft(audio_samples)
                freqs = np.fft.fftfreq(len(spectrum), d=1 / framerate)

                # Filtrar frecuencias positivas
                positive_freqs = freqs[:len(freqs) // 2]
                positive_spectrum = np.abs(spectrum[:len(spectrum) // 2])

                # Calcular decibeles
                amplitudes = np.abs(audio_samples)
                decibeles = 20 * np.log10(amplitudes + 1e-6)  # Evitar log(0)

                # Graficar espectro de frecuencia
                plt.figure(figsize=(12, 6))

                plt.subplot(2, 1, 1)
                plt.plot(positive_freqs, positive_spectrum)
                plt.title("Espectro de Frecuencia")
                plt.xlabel("Frecuencia (Hz)")
                plt.ylabel("Amplitud")
                plt.grid()

                # Graficar decibeles en el tiempo
                plt.subplot(2, 1, 2)
                plt.plot(tiempo, decibeles)
                plt.title("Nivel de Decibeles en el Tiempo")
                plt.xlabel("Tiempo (s)")
                plt.ylabel("Decibeles (dB)")
                plt.grid()

                plt.tight_layout()
                plt.show()
        except Exception as e:
            print(f"Error al graficar espectro: {e}")

        
    def escuchar_continuamente(self):
        """Escucha continuamente y procesa preguntas cuando se detecta la palabra clave."""
        with sr.Microphone(device_index=0) as source:
            print("Esperando la palabra clave...")
            self.ajustar_ruido_ambiental(source)
            self.persona_id = 0

            while self.escuchando:
                try:
                    # Escuchar audio y convertir a texto
                    audio = self.reconocedor.listen(source, timeout=100)
                    texto = self.reconocedor.recognize_google(audio, language=self.language).lower()
                    print(f"Escuchado: {texto}")

                    if texto.strip() == self.keyword:
                        self.persona_id += 1
                        print(f"Palabra clave '{self.keyword}' detectada. Iniciando conversación.")
                        self.reproducir_respuesta("Hola, soy el Bot. ¿En qué puedo ayudarte?")

                        # Procesar preguntas de la conversación
                        while True:
                            try:
                                print("Esperando pregunta...")
                                pregunta_audio = self.reconocedor.listen(source, timeout=100)
                                pregunta_texto = self.reconocedor.recognize_google(pregunta_audio, language=self.language).lower()
                                print(f"Pregunta escuchada: {pregunta_texto}")

                                # Obtener datos de audio crudo
                                audio_data = pregunta_audio.get_wav_data()
                                
                                self.graficar_espectro(audio_data)


                                # Calcular frecuencia dominante
                                frecuencia = self.calcular_frecuencia_dominante(audio_data)
                                print(f"Frecuencia dominante: {frecuencia} Hz")

                                # Detectar cierre de conversación
                                if pregunta_texto.strip() == "gracias":
                                    self.reproducir_respuesta("Gracias por hablar conmigo. ¡Adiós!")
                                    print("Conversación terminada.")
                                    break

                                # Obtener respuesta del chatbot
                                respuesta = self.chatbot_app.enviar_mensaje(pregunta_texto)
                                print(f"Respuesta del ChatBot: {respuesta}")
                                self.reproducir_respuesta(respuesta)

                                # Guardar en JSON
                                self.guardar_en_json(
                                    persona=f"Persona {self.persona_id}",
                                    pregunta=pregunta_texto,
                                    respuesta=respuesta,
                                    frecuencia=frecuencia
                                )
                            except sr.UnknownValueError:
                                self.reproducir_respuesta("No entendí lo que dijiste. Intenta de nuevo.")
                            except sr.RequestError as e:
                                self.reproducir_respuesta(f"Error con el reconocimiento de voz: {e}. Terminando conversación.")
                                break
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"Error con el reconocimiento de voz: {e}")
                    break
