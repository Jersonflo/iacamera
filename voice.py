import speech_recognition as sr

# Inicializar el reconocedor
reconocedor = sr.Recognizer()

# Utilizar el micrófono como fuente de entrada
with sr.Microphone() as source:
    print("Di algo...")
    # Ajusta el ruido ambiental para mejorar el reconocimiento
    reconocedor.adjust_for_ambient_noise(source)
    
    # Escucha la entrada de audio
    audio = reconocedor.listen(source)
    
    try:
        # Convierte el audio en texto
        texto = reconocedor.recognize_google(audio, language="es-ES")
        print("Has dicho: " + texto)
    except sr.UnknownValueError:
        print("No se pudo entender el audio.")
    except sr.RequestError:
        print("No se pudo obtener resultados del servicio de reconocimiento de voz.")
