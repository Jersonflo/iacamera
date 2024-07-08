import serial
import time

# Configura la conexión serial para macOS (ajusta el puerto según sea necesario)
ser = serial.Serial('/dev/cu.usbserial-0001', 9600)  # Reemplaza con el puerto serial correcto

def send_message(message):
    ser.write(f"{message}\n".encode())  # Envía el mensaje al ESP32
    print(f"Enviado: {message}")  # Imprime el mensaje enviado
    time.sleep(1)  # Espera un poco para asegurarse de que el ESP32 reciba los datos

# Prueba enviando diferentes mensajes
send_message("Hola, ESP32")
time.sleep(2)
send_message("Controlando el servo desde Python")
time.sleep(2)
send_message("Mensaje final")

ser.close()  # Cierra la conexión serial
