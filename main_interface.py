import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QIcon
from robot_control import RobotCameraController  # Importa la clase del controlador del robot

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventana Principal")
        self.setGeometry(100, 100, 800, 600)

        # Layout principal
        layout_principal = QVBoxLayout()

        # Logo
        self.logo = QLabel("LOGO AQUÍ")
        self.logo.setAlignment(Qt.AlignCenter)
        layout_principal.addWidget(self.logo)

        # Área de visualización de la cámara
        self.camara_label = QLabel()
        self.camara_label.setFixedSize(640, 480)  # Ajusta el tamaño del área de visualización
        layout_principal.addWidget(self.camara_label)

        # Configuración de la sección de botones
        layout_botones = QHBoxLayout()

        # Botón de Iniciar
        self.iniciar_boton = QPushButton("Iniciar")
        self.iniciar_boton.clicked.connect(self.iniciar_camara)
        layout_botones.addWidget(self.iniciar_boton)

        # Botón de Detener
        self.detener_boton = QPushButton("Detener")
        self.detener_boton.clicked.connect(self.detener_camara)
        layout_botones.addWidget(self.detener_boton)

        # Botón de Conócenos
        self.conocenos_boton = QPushButton("Conócenos")
        self.conocenos_boton.clicked.connect(self.mostrar_mensaje_conocenos)
        layout_botones.addWidget(self.conocenos_boton)

        # Botón de Ayuda (circular con un signo de interrogación)
        self.ayuda_boton = QPushButton("?")
        self.ayuda_boton.setFixedSize(40, 40)  # Tamaño del botón
        self.ayuda_boton.setStyleSheet("border-radius: 20px; background-color: lightblue;")
        self.ayuda_boton.clicked.connect(self.mostrar_ayuda)
        layout_botones.addWidget(self.ayuda_boton)

        # Agregar el layout de los botones al layout principal
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        # Inicialización del controlador de la cámara del robot
        self.robot_controller = RobotCameraController(serial_port='/dev/tty.usbserial-0001')
        
        # Configuración del QTimer para actualizar la imagen cada 30 ms
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)

    def iniciar_camara(self):
        """Inicia la cámara y muestra el video en el área de visualización."""
        self.timer.start(30)  # Inicia el temporizador para actualizar la imagen

    def detener_camara(self):
        """Detiene la cámara y limpia el área de visualización."""
        self.timer.stop()
        self.robot_controller._enviar_comando(b'p')  # Envía el comando para detener el robot
        self.robot_controller.limpiar()  # Libera los recursos de la cámara
        self.camara_label.clear()  # Limpia la vista de la cámara

    def update_image(self):
        """Captura un nuevo cuadro de la cámara y lo muestra en la etiqueta de la interfaz."""
        qt_image = self.robot_controller.capturar_cuadro()
        if qt_image:
            self.camara_label.setPixmap(QPixmap.fromImage(qt_image))

    def mostrar_mensaje_conocenos(self):
        """Muestra un mensaje al hacer clic en el botón Conócenos."""
        QMessageBox.information(self, "Conócenos", "Este es un proyecto para el seguimiento visual y control de un robot.")

    def mostrar_ayuda(self):
        """Muestra una ventana emergente con las instrucciones de uso."""
        mensaje_ayuda = (
            "Instrucciones de Uso:\n"
            "- Iniciar: Comienza la transmisión de la cámara y el seguimiento del rostro.\n"
            "- Detener: Detiene la transmisión y el seguimiento del rostro.\n"
            "- Conócenos: Muestra información sobre el proyecto.\n"
            "- ?: Abre esta ventana de ayuda."
        )
        QMessageBox.information(self, "Ayuda", mensaje_ayuda)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec_())
