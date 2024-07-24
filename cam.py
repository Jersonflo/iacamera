import cv2
import numpy as np
from math import sqrt
import serial
import time


# Configurar la conexión serie
try:
    ser = serial.Serial('/dev/tty.usbserial-0001', 9600)  # Reemplaza con el puerto correcto
    d = 'd'
    i = 'i'
    p = 'p'

    time.sleep(5)  # Esperar a que la conexión se establezca
except serial.SerialException as e:
    print(f"No se puede abrir el puerto serial: {e}")
    exit()
# Función para calcular el área de intersección de dos rectángulos
def calcular_area_interseccion(x1, y1, x2, y2, x3, y3, x4, y4):
    inter_x1 = max(x1, x3)
    inter_y1 = max(y1, y3)
    inter_x2 = min(x2, x4)
    inter_y2 = min(y2, y4)
    if inter_x1 < inter_x2 and inter_y1 < inter_y2:
        inter_width = inter_x2 - inter_x1
        inter_height = inter_y2 - inter_y1
        return inter_width * inter_height
    return 0

# Cargar el modelo de DNN
net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("No se puede abrir la cámara")
    exit()

prev_cx = None

# Criterio para seleccionar el rostro a seguir: 'size' o 'distance'
selection_criteria = 'size'  # Cambiar a 'distance' para usar la distancia

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo capturar el frame de la cámara")
        break

    # Convertimos a blob y realizamos la detección de rostros
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    h, w = frame.shape[:2]
    faces = []

    # Filtramos todas las detecciones con una confianza mayor a 0.5
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            faces.append((x1, y1, x2, y2))

    if len(faces) > 0:
        if selection_criteria == 'distance':
            # Seleccionamos el rostro más cercano (asumiendo que el rostro más cercano está más cerca del centro vertical)
            face = min(faces, key=lambda rect: rect[1])
        else:  # 'size'
            # Seleccionamos la cara más grande
            face = faces[0]

        (x1, y1, x2, y2) = face
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (cx, 0), (cx, frame.shape[0]), (0, 0, 255), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)  

        # Conversión de píxeles a centímetros (1 píxel = 0.0264583 cm)
        pixel_to_cm = 0.0264583
        width_cm = (x2 - x1) * pixel_to_cm
        height_cm = (y2 - y1) * pixel_to_cm
        area_cm2 = width_cm * height_cm

        # Mostrar las coordenadas y el área en la terminal para el rostro seleccionado
       # print(f"Rostro seleccionado - Coordenadas: (X1, Y1) = ({x1}, {y1}), (X2, Y2) = ({x2}, {y2})")
       # print(f"Rostro seleccionado - Área: {area_cm2:.2f} cm^2")

        total_area_cm2 = (w * h) * (pixel_to_cm ** 2)
        # print(f"Área total de la ventana: {total_area_cm2:.2f} cm^2")

        if len(faces) > 1:
            (x3, y3, x4, y4) = faces[1]
            cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 255, 0), 2)
            cx2, cy2 = (x3 + x4) // 2, (y3 + y4) // 2
            cv2.line(frame, (cx2, 0), (cx2, frame.shape[0]), (0, 0, 255), 2)
            cv2.circle(frame, (cx2, cy2), 5, (0, 0, 255), -1)  

            width2_cm = (x4 - x3) * pixel_to_cm
            height2_cm = (y4 - y3) * pixel_to_cm
            area2_cm2 = width2_cm * height2_cm

            # Calculamos el área de intersección
            area_interseccion = calcular_area_interseccion(x1, y1, x2, y2, x3, y3, x4, y4) * (pixel_to_cm ** 2)

            # Área total menos áreas de los rostros y la intersección (si aplica)
            area_final_cm2 = total_area_cm2 - area_cm2 - area2_cm2 + area_interseccion

            # Mostrar las coordenadas y el área en la terminal para el segundo rostro
            # print(f"Rostro 2 - Coordenadas: (X1, Y1) = ({x3}, {y3}), (X2, Y2) = ({x4}, {y4})")
             #print(f"Rostro 2 - Área: {area2_cm2:.2f} cm^2")
             #print(f"Área de intersección: {area_interseccion:.2f} cm^2")
             #print(f"Área final: {area_final_cm2:.2f} cm^2")
        else:
            # Si solo hay un rostro, el área final es el área total de la ventana menos el área del rostro
            area_final_cm2 = total_area_cm2 - area_cm2
            # print(f"Área final: {area_final_cm2:.2f} cm^2")

        # Lógica para determinar movimiento
        if prev_cx is not None:
            if cx < prev_cx - 50:
                print("Izquierda")
                ser.write(i.encode('ascii'))  # Enviar comando 'i' para mover el servo a la izquierda
            elif cx > prev_cx + 50:
                print("Derecha")
                ser.write(d.encode('ascii'))  # Enviar comando 'd' para mover el servo a la derecha
            else:
                print("Parar")
                ser.write(p.encode('ascii'))  # Enviar comando 'p' para parar el servo
        prev_cx = cx

    cv2.imshow("Camara", frame)
    t = cv2.waitKey(1)
    if t == 27:
        break   


cap.release()
cv2.destroyAllWindows()
ser.close()