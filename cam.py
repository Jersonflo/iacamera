import cv2
import numpy as np


# Cargar el modelo de DNN
net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("No se puede abrir la cámara")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo capturar el frame de la cámara")
        break

    # Convertimos a blob y realizamos la detección de rostros
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    # Filtramos la detección con mayor confianza
    h, w = frame.shape[:2]
    max_confidence = 0
    max_idx = 0
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > max_confidence:
            max_confidence = confidence
            max_idx = i

    if max_confidence > 0.5:
        box = detections[0, 0, max_idx, 3:7] * np.array([w, h, w, h])
        (x, y, x1, y1) = box.astype("int")
        cv2.rectangle(frame, (x, y), (x1, y1), (0, 255, 0), 2)
        cx, cy = (x + x1) // 2, (y + y1) // 2
        cv2.line(frame, (cx, 0), (cx, frame.shape[0]), (0, 0, 255), 2)

    cv2.imshow("Camara", frame)
    t = cv2.waitKey(1)
    if t == 27:
        break

cap.release()
cv2.destroyAllWindows()
