from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer
from robot_control import RobotCameraController

class CameraWindow(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setWindowTitle("Ventana de Cámara")
        self.setGeometry(100, 100, 800, 600)

        # Layout principal
        layout_principal = QVBoxLayout()
        self.camara_label = QLabel()
        layout_principal.addWidget(self.camara_label)

        # Botones de control
        regresar_boton = QPushButton("Regresar")
        regresar_boton.clicked.connect(self.regresar)
        layout_principal.addWidget(regresar_boton)
        self.setLayout(layout_principal)

        # Instancia de RobotCameraController
        self.robot_controller = RobotCameraController(serial_port='/dev/tty.usbserial-0001')

        # Configuración del QTimer para actualizar la imagen cada 30 ms
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)

    def iniciar_camara(self):
        """Inicia la cámara y la actualización de imágenes."""
        self.timer.start(30)

    def detener_camara(self):
        """Detiene la actualización de imágenes, envía el comando de detención y limpia el controlador."""
        # Envía el comando 'p' para detener el movimiento del robot
        self.robot_controller._enviar_comando(b'p')
        self.timer.stop()
        self.robot_controller.limpiar()

    def update_image(self):
        """Captura un nuevo cuadro y lo muestra en la etiqueta."""
        qt_image = self.robot_controller.capturar_cuadro()
        if qt_image:
            self.camara_label.setPixmap(QPixmap.fromImage(qt_image))

    def regresar(self):
        """Regresa a la ventana principal y detiene la cámara."""
        self.detener_camara()
        self.stacked_widget.setCurrentIndex(0)
