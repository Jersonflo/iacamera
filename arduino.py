import serial
import time

# Configura la conexión serial con el ESP32
ser = serial.Serial('/dev/cu.usbserial-0001', 115200)  

# Espera un poco para asegurarse de que la conexión se haya establecido
time.sleep(2)

try:
    while True:
        # Envía un mensaje al ESP32
        ser.write(b'Hola ESP32!\n')

        # Lee la respuesta del ESP32
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').rstrip()
            print(f'Respuesta del ESP32: {response}')

        time.sleep(1)  # Espera un segundo antes de enviar el siguiente mensaje

except KeyboardInterrupt:
    print('Terminando la conexión')
    ser.close()
