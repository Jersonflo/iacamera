import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import cv2

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana principal
        self.setWindowTitle("Interfaz de Cámara")
        self.setGeometry(100, 100, 800, 600)
        
        # Layouts
        self.layout_principal = QVBoxLayout()
        self.layout_botones = QHBoxLayout()
        
        # Etiqueta para mostrar la cámara
        self.camara_label = QLabel()
        self.layout_principal.addWidget(self.camara_label)
        
        # Botones
        self.iniciar_boton = QPushButton("Iniciar")
        self.detener_boton = QPushButton("Detener")
        self.escuchar_boton = QPushButton("Escuchar")
        
        # Añadir botones al layout de botones
        self.layout_botones.addWidget(self.iniciar_boton)
        self.layout_botones.addWidget(self.detener_boton)
        self.layout_botones.addWidget(self.escuchar_boton)
        
        # Añadir layout de botones al layout principal
        self.layout_principal.addLayout(self.layout_botones)
        
        # Configuración de eventos
        self.iniciar_boton.clicked.connect(self.iniciar_camara)
        self.detener_boton.clicked.connect(self.detener_camara)
        self.escuchar_boton.clicked.connect(self.escuchar)
        
        # Configuración de cámara
        self.timer = QTimer()
        self.timer.timeout.connect(self.mostrar_camara)
        self.cap = None
        
        # Establecer layout principal
        self.setLayout(self.layout_principal)
    
    def iniciar_camara(self):
        self.cap = cv2.VideoCapture(0)  # Abre la cámara
        self.timer.start(20)  # Dispara el temporizador para capturar cada cuadro
    
    def detener_camara(self):
        if self.cap:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.camara_label.clear()
    
    def mostrar_camara(self):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Convierte el cuadro a formato RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                # Convierte a QImage para mostrar en QLabel
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.camara_label.setPixmap(QPixmap.fromImage(qt_image))
    
    def escuchar(self):
        print("Escuchando...")  # Aquí puedes añadir la funcionalidad de escucha deseada

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = CameraApp()
    ventana.show()
    sys.exit(app.exec_())
