import cv2
import numpy as np
import serial
import time
from PyQt5.QtGui import QImage


class RobotCameraController:
    def __init__(self, serial_port, baud_rate=9600, dead_zone_width=300, dead_zone_height=300, selection_criteria='size'):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.dead_zone_width = dead_zone_width
        self.dead_zone_height = dead_zone_height
        self.selection_criteria = selection_criteria
        self.pixel_to_cm = 0.0264583

        # Inicializar la conexión serial
        self._init_serial()

        # Cargar el modelo DNN para la detección de rostros
        self.net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')

        # Configurar la cámara
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            print("No se puede abrir la cámara")
            exit()

    def _init_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate)
            time.sleep(5)
        except serial.SerialException as e:
            print(f"No se puede abrir el puerto serial: {e}")
            self.ser = None

    def capturar_cuadro(self):
        """Captura un cuadro, procesa la detección y envía comandos de movimiento."""
        ret, frame = self.cap.read()
        if not ret:
            print("No se pudo capturar el frame de la cámara")
            return None

        frame = cv2.flip(frame, 1)
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.net.setInput(blob)
        detections = self.net.forward()

        h, w = frame.shape[:2]
        faces = []

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")
                faces.append((x1, y1, x2, y2))

        if faces:
            face = self._seleccionar_rostro(faces, h)
            self._dibujar_elementos(frame, face, faces, h, w)
            self._mover_robot(face, w, h)

        # Convertir el frame a QImage para PyQt5
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return qt_image

    def _seleccionar_rostro(self, faces, h):
        """Selecciona el rostro a seguir basado en el criterio establecido."""
        if self.selection_criteria == 'size':
            return max(faces, key=lambda rect: (rect[2] - rect[0]) * (rect[3] - rect[1]))
        else:
            return min(faces, key=lambda rect: abs((rect[1] + rect[3]) / 2 - h / 2))

    def _dibujar_elementos(self, frame, face, faces, h, w):
        """Dibuja el rectángulo de los rostros y la zona muerta en el frame."""
        (x1, y1, x2, y2) = face
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.line(frame, (cx, 0), (cx, frame.shape[0]), (0, 0, 255), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        # Calcula el tamaño del rectángulo azul en función del rectángulo del rostro detectado
        face_width = x2 - x1
        face_height = y2 - y1
        dead_zone_width = min(self.dead_zone_width, face_width * 2)
        dead_zone_height = min(self.dead_zone_height, face_height * 2)
    
        # Define las esquinas del rectángulo azul
        frame_cx, frame_cy = w // 2, h // 2
        top_left = (frame_cx - dead_zone_width // 2, frame_cy - dead_zone_height // 2)
        bottom_right = (frame_cx + dead_zone_width // 2, frame_cy + dead_zone_height // 2)

        # Dibuja el rectángulo azul de la zona muerta
        cv2.rectangle(frame, top_left, bottom_right, (255, 0, 0), 2)

    def _mover_robot(self, face, w, h):
        """Controla el movimiento del robot según la posición del rostro."""
        (x1, y1, x2, y2) = face
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        frame_cx, frame_cy = w // 2, h // 2

        diff_x, diff_y = cx - frame_cx, cy - frame_cy

        # Movimiento horizontal
        if abs(diff_x) > self.dead_zone_width // 2:
            if diff_x < 0:
                print("Izquierda")
                self._enviar_comando(b'i')
            else:
                print("Derecha")
                self._enviar_comando(b'd')

        # Movimiento vertical
        if abs(diff_y) > self.dead_zone_height // 2:
            if diff_y < 0:
                print("Arriba")
                self._enviar_comando(b'b')
            else:
                print("Abajo")
                self._enviar_comando(b'a')

    def _enviar_comando(self, comando):
        """Envía un comando al robot a través de la conexión serial."""
        if self.ser:
            self.ser.write(comando)
            time.sleep(0.15)

    def limpiar(self):
        self.cap.release()
        cv2.destroyAllWindows()
        if self.ser:
            self.ser.close()
        print("Recursos liberados.")