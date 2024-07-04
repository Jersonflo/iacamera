import cv2
import numpy as np
from screeninfo import get_monitors
from math import sqrt
import tkinter as tk

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

# Función para calcular el PPI
def calculate_ppi(resolution_width, resolution_height, diagonal_size_inch):
    diagonal_resolution = (resolution_width**2 + resolution_height**2) ** 0.5
    ppi = diagonal_resolution / diagonal_size_inch
    return ppi

# Obtener la resolución de la pantalla y el tamaño diagonal en pulgadas usando tkinter
def get_screen_info():
    root = tk.Tk()
    resolution_width = root.winfo_screenwidth()
    resolution_height = root.winfo_screenheight()
    root.destroy()

    # Intentar obtener la información de la pantalla con screeninfo
    monitor = get_monitors()[0]
    width_mm = monitor.width_mm
    height_mm = monitor.height_mm

    if width_mm is None or height_mm is None:
        # Si no se pudo obtener la información física, usar valores predeterminados
        raise ValueError("No se pudo obtener la información física de la pantalla.")

    # Calcular el tamaño diagonal en pulgadas
    diagonal_size_inch = sqrt(width_mm**2 + height_mm**2) / 25.4
    return resolution_width, resolution_height, diagonal_size_inch

# Cargar el modelo de DNN
net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("No se puede abrir la cámara")
    exit()

try:
    resolution_width, resolution_height, diagonal_size_inch = get_screen_info()
except ValueError as e:
    print(e)
    exit()

ppi = calculate_ppi(resolution_width, resolution_height, diagonal_size_inch)

print(f"Screen resolution: {resolution_width} x {resolution_height}")
print(f"Diagonal size: {diagonal_size_inch:.2f} inches")
print(f"Calculated PPI: {ppi:.2f}")

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

    # Ordenamos las caras detectadas por el tamaño (área del rectángulo)
    faces = sorted(faces, key=lambda x: (x[2] - x[0]) * (x[3] - x[1]), reverse=True)

    if len(faces) > 0:
        # Seleccionamos la cara más grande
        (x1, y1, x2, y2) = faces[0]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cx1, cy1 = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (cx1, 0), (cx1, frame.shape[0]), (0, 0, 255), 2)

        # Conversión de píxeles a centímetros usando PPI
        pixel_to_cm = 2.54 / ppi
        width1_cm = (x2 - x1) * pixel_to_cm
        height1_cm = (y2 - y1) * pixel_to_cm
        area1_cm2 = width1_cm * height1_cm

        # Mostrar las coordenadas y el área en la terminal para el primer rostro
        print(f"Rostro 1 - Área: {area1_cm2:.2f} cm^2")

        total_area_cm2 = (resolution_width * resolution_height) * (pixel_to_cm ** 2)

        if len(faces) > 1:
            (x3, y3, x4, y4) = faces[1]
            cv2.rectangle(frame, (x3, y3), (x4, y4), (0, 255, 0), 2)
            cx2, cy2 = (x3 + x4) // 2, (y3 + y4) // 2
            cv2.line(frame, (cx2, 0), (cx2, frame.shape[0]), (0, 0, 255), 2)

            width2_cm = (x4 - x3) * pixel_to_cm
            height2_cm = (y4 - y3) * pixel_to_cm
            area2_cm2 = width2_cm * height2_cm

            # Calculamos el área de intersección
            area_interseccion = calcular_area_interseccion(x1, y1, x2, y2, x3, y3, x4, y4) * (pixel_to_cm ** 2)

            # Área total menos áreas de los rostros y la intersección (si aplica)
            area_final_cm2 = total_area_cm2 - area1_cm2 - area2_cm2 + area_interseccion

            # Mostrar las coordenadas y el área en la terminal para el segundo rostro
            print(f"Rostro 2 - Área: {area2_cm2:.2f} cm^2")
            print(f"Área de intersección: {area_interseccion:.2f} cm^2")
            print(f"Área final: {area_final_cm2:.2f} cm^2")
        else:
            # Si solo hay un rostro, el área final es el área total de la ventana menos el área del rostro
            area_final_cm2 = total_area_cm2 - area1_cm2
            print(f"Área final: {area_final_cm2:.2f} cm^2")

    cv2.imshow("Camara", frame)
    t = cv2.waitKey(1)
    if t == 27:
        break

cap.release()
cv2.destroyAllWindows()
