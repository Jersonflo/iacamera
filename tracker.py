import cv2
import serial
import time
import mediapipe as mp
from datetime import datetime


class FaceTracker:
    def __init__(
        self,
        serial_port='/dev/cu.usbserial-0001',
        baud_rate=9600,
        dead_zone_width=300,
        dead_zone_height=300,
        camera_index=1,
        robot_mode=True
    ):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.dead_zone_width = dead_zone_width
        self.dead_zone_height = dead_zone_height
        self.robot_mode = robot_mode  # False = solo visión, sin envío serial

        # ── FPS ──────────────────────────────────────────────
        self._fps = 0.0
        self._frame_count = 0
        self._fps_timer = time.time()

        # ── Datos del último rostro detectado ─────────────────
        self.face_data = {
            "detected": False,
            "confidence": 0.0,
            "pos_x_pct": 0.0,   # 0–100%
            "pos_y_pct": 0.0,
            "num_faces": 0,
            "robot_state": "Esperando",
        }

        # ── MediaPipe ─────────────────────────────────────────
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.97
        )

        # ── Serial ────────────────────────────────────────────
        self.ser = None
        if self.robot_mode:
            self._init_serial()

        # ── Cámara ────────────────────────────────────────────
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)

    # ─────────────────────────────────────────────────────────
    # Inicialización
    # ─────────────────────────────────────────────────────────
    def _init_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate)
            time.sleep(2)
            print(f"[Serial] Conectado a {self.serial_port}")
        except serial.SerialException as e:
            print(f"[Serial] No se puede abrir el puerto: {e}")
            self.ser = None

    def cambiar_camara(self, index: int):
        """Cambia el índice de la cámara sin reiniciar el tracker."""
        if self.cap.isOpened():
            self.cap.release()
        self.camera_index = index
        self.cap = cv2.VideoCapture(index)

    def set_robot_mode(self, enabled: bool):
        """Activa o desactiva el envío de comandos al robot."""
        self.robot_mode = enabled
        if enabled and self.ser is None:
            self._init_serial()

    # ─────────────────────────────────────────────────────────
    # Bucle principal
    # ─────────────────────────────────────────────────────────
    def capturar_y_procesar(self):
        """Captura un frame, detecta rostros, dibuja overlays y envía comandos."""
        if not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            return None

        # Calcular FPS
        self._frame_count += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = time.time()

        # Espejo natural
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Detectar rostros
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)

        faces = []
        confidences = []
        if results.detections:
            for detection in results.detections:
                score = detection.score[0] if detection.score else 0.0
                bboxC = detection.location_data.relative_bounding_box
                x1 = int(bboxC.xmin * w)
                y1 = int(bboxC.ymin * h)
                x2 = x1 + int(bboxC.width * w)
                y2 = y1 + int(bboxC.height * h)
                faces.append((x1, y1, x2, y2))
                confidences.append(score)

        self.face_data["num_faces"] = len(faces)

        if faces:
            # Seleccionar el rostro más grande
            idx = max(range(len(faces)), key=lambda i: (faces[i][2]-faces[i][0])*(faces[i][3]-faces[i][1]))
            face = faces[idx]
            conf = confidences[idx]

            cx, cy = (face[0]+face[2])//2, (face[1]+face[3])//2
            self.face_data["detected"] = True
            self.face_data["confidence"] = conf
            self.face_data["pos_x_pct"] = round(cx / w * 100, 1)
            self.face_data["pos_y_pct"] = round(cy / h * 100, 1)

            self._dibujar_elementos(frame, face, w, h, conf)
            cmd = self._mover_robot(face, w, h)
            self.face_data["robot_state"] = cmd if cmd else "Centrado"
        else:
            self.face_data["detected"] = False
            self.face_data["confidence"] = 0.0
            self.face_data["pos_x_pct"] = 0.0
            self.face_data["pos_y_pct"] = 0.0
            self.face_data["robot_state"] = "Buscando..."
            self._dibujar_zona_muerta_default(frame, w, h)

        # Overlay: FPS + timestamp
        self._dibujar_overlay_info(frame, w, h)

        return frame

    # ─────────────────────────────────────────────────────────
    # Dibujo
    # ─────────────────────────────────────────────────────────
    def _dibujar_overlay_info(self, frame, w, h):
        """Dibuja FPS y timestamp en el frame."""
        # FPS — esquina superior izquierda
        fps_text = f"FPS: {self._fps:.1f}"
        cv2.putText(frame, fps_text, (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 212, 255), 2, cv2.LINE_AA)

        # Timestamp — esquina inferior derecha
        ts = datetime.now().strftime("%H:%M:%S")
        ts_size, _ = cv2.getTextSize(ts, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(frame, ts, (w - ts_size[0] - 10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)

        # Modo — esquina superior derecha
        modo = "CON ROBOT" if self.robot_mode else "SOLO VISIÓN"
        color_modo = (0, 255, 136) if self.robot_mode else (0, 212, 255)
        modo_size, _ = cv2.getTextSize(modo, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(frame, modo, (w - modo_size[0] - 10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_modo, 1, cv2.LINE_AA)

    def _dibujar_zona_muerta_default(self, frame, w, h):
        frame_cx, frame_cy = w // 2, h // 2
        tl = (frame_cx - self.dead_zone_width//2, frame_cy - self.dead_zone_height//2)
        br = (frame_cx + self.dead_zone_width//2, frame_cy + self.dead_zone_height//2)
        # Zona muerta con esquinas estilo HUD
        self._dibujar_hud_rect(frame, tl, br, (0, 140, 255))

    def _dibujar_elementos(self, frame, face, w, h, conf):
        x1, y1, x2, y2 = face
        cx, cy = (x1+x2)//2, (y1+y2)//2

        # Bounding box del rostro (verde neón)
        self._dibujar_hud_rect(frame, (x1, y1), (x2, y2), (0, 255, 136))

        # Líneas de crosshair
        cv2.line(frame, (cx, 0), (cx, h), (0, 200, 255), 1, cv2.LINE_AA)
        cv2.line(frame, (0, cy), (w, cy), (0, 200, 255), 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 6, (0, 200, 255), -1)
        cv2.circle(frame, (cx, cy), 12, (0, 200, 255), 1)

        # Confianza
        conf_text = f"{conf*100:.1f}%"
        cv2.putText(frame, conf_text, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 136), 1, cv2.LINE_AA)

        # Zona muerta dinámica
        face_w, face_h = x2-x1, y2-y1
        dz_w = min(self.dead_zone_width, face_w*2)
        dz_h = min(self.dead_zone_height, face_h*2)
        frame_cx, frame_cy = w//2, h//2
        tl = (frame_cx - dz_w//2, frame_cy - dz_h//2)
        br = (frame_cx + dz_w//2, frame_cy + dz_h//2)
        self._dibujar_hud_rect(frame, tl, br, (0, 140, 255))

    def _dibujar_hud_rect(self, frame, tl, br, color, length=20, thickness=2):
        """Dibuja un rectángulo estilo HUD con solo las esquinas."""
        x1, y1 = tl
        x2, y2 = br
        # Esquina TL
        cv2.line(frame, (x1, y1), (x1 + length, y1), color, thickness)
        cv2.line(frame, (x1, y1), (x1, y1 + length), color, thickness)
        # Esquina TR
        cv2.line(frame, (x2, y1), (x2 - length, y1), color, thickness)
        cv2.line(frame, (x2, y1), (x2, y1 + length), color, thickness)
        # Esquina BL
        cv2.line(frame, (x1, y2), (x1 + length, y2), color, thickness)
        cv2.line(frame, (x1, y2), (x1, y2 - length), color, thickness)
        # Esquina BR
        cv2.line(frame, (x2, y2), (x2 - length, y2), color, thickness)
        cv2.line(frame, (x2, y2), (x2, y2 - length), color, thickness)

    # ─────────────────────────────────────────────────────────
    # Control del robot
    # ─────────────────────────────────────────────────────────
    def _mover_robot(self, face, w, h) -> str | None:
        x1, y1, x2, y2 = face
        cx, cy = (x1+x2)//2, (y1+y2)//2
        frame_cx, frame_cy = w//2, h//2
        diff_x = cx - frame_cx
        diff_y = cy - frame_cy

        face_w, face_h = x2-x1, y2-y1
        dz_w = min(self.dead_zone_width, face_w*2)
        dz_h = min(self.dead_zone_height, face_h*2)

        cmd_label = None

        if abs(diff_x) > dz_w//2:
            if diff_x < 0:
                cmd_label = "← Izquierda"
                self._enviar_comando(b'i')
            else:
                cmd_label = "→ Derecha"
                self._enviar_comando(b'd')

        if abs(diff_y) > dz_h//2:
            if diff_y < 0:
                suffix = "↑ Arriba"
                self._enviar_comando(b'b')
            else:
                suffix = "↓ Abajo"
                self._enviar_comando(b'a')
            cmd_label = f"{cmd_label} {suffix}" if cmd_label else suffix

        return cmd_label

    def _enviar_comando(self, comando):
        if self.robot_mode and self.ser:
            self.ser.write(comando)
            time.sleep(0.05)

    # ─────────────────────────────────────────────────────────
    # Propiedades expuestas a la UI
    # ─────────────────────────────────────────────────────────
    @property
    def fps(self) -> float:
        return round(self._fps, 1)

    @property
    def serial_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    # ─────────────────────────────────────────────────────────
    # Limpieza
    # ─────────────────────────────────────────────────────────
    def limpiar(self):
        if self.cap.isOpened():
            self.cap.release()
        if self.ser:
            self.ser.close()
        self.face_detection.close()
        print("[Tracker] Recursos liberados.")
