import sys
import pyttsx3 
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QIcon
from robot_control import RobotCameraController 


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventana Principal")
        self.setGeometry(100, 100, 1200, 800)

         # Inicialización del motor de texto a voz
        self.engine = pyttsx3.init()
        self.reproducir_mensaje_inicial("Bienvenido al sistema de control y seguimiento visual del robot de Ecosystem, mírame fijamente para detectar tu rostro. Dale click en el Botón Inicar para poder moverme.")


        # Layout principal
        layout_principal = QHBoxLayout()

        # Layout izquierdo (logo y área de cámara)
        layout_izquierdo = QVBoxLayout()


        # Área de visualización de la cámara
        self.camara_label = QLabel()
        self.camara_label.setFixedSize(900, 500)  
        layout_izquierdo.addWidget(self.camara_label)

        layout_principal.addLayout(layout_izquierdo)

        # Layout derecho (botones)
        layout_derecho = QVBoxLayout()

                # Logo
        self.logo = QLabel("LOGO AQUÍ")
        self.logo.setAlignment(Qt.AlignCenter)
        layout_derecho.addWidget(self.logo)

         # Espaciador superior para centrar los botones
        layout_derecho.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Botón de Iniciar
        self.iniciar_boton = QPushButton("Iniciar")
        self.iniciar_boton.clicked.connect(self.iniciar_camara)
        layout_derecho.addWidget(self.iniciar_boton)

        # Botón de Detener
        self.detener_boton = QPushButton("Detener")
        self.detener_boton.clicked.connect(self.detener_camara)
        layout_derecho.addWidget(self.detener_boton)

        # Botón de Conócenos
        self.conocenos_boton = QPushButton("Conócenos")
        self.conocenos_boton.clicked.connect(self.mostrar_mensaje_conocenos)
        layout_derecho.addWidget(self.conocenos_boton, )

        # Espaciador inferior para centrar los botones
        layout_derecho.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))


        # Botón de Ayuda (circular con un signo de interrogación en la esquina inferior derecha)
        self.ayuda_boton = QPushButton("?")
        self.ayuda_boton.setFixedSize(40, 40)  # Tamaño del botón
        self.ayuda_boton.setStyleSheet("border-radius: 20px; background-color: lightblue;")
        self.ayuda_boton.clicked.connect(self.mostrar_ayuda)
        layout_derecho.addWidget(self.ayuda_boton, alignment=Qt.AlignRight | Qt.AlignBottom)

        layout_principal.addLayout(layout_derecho)
        self.setLayout(layout_principal)

        # Inicialización del controlador de la cámara del robot (se re-inicializa en iniciar_camara)
        self.robot_controller = None
        
        # Configuración del QTimer para actualizar la imagen cada 30 ms
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
    

    def reproducir_mensaje_inicial(self, mensaje):
        """Reproduce un mensaje de bienvenida al iniciar la aplicación."""
        self.engine.say(mensaje)
        self.engine.runAndWait()


    def iniciar_camara(self):
            """Inicia la cámara y el controlador del robot."""
            if not self.robot_controller:
                # Re-inicializa el controlador de la cámara y del robot
                self.robot_controller = RobotCameraController(serial_port='/dev/tty.usbserial-0001')
            self.timer.start(30)  # Inicia el temporizador para actualizar la imagen

    def detener_camara(self):
        """Detiene la cámara y limpia el área de visualización."""
        self.timer.stop()
        if self.robot_controller:
            self.robot_controller._enviar_comando(b'p')  # Envía el comando para detener el robot
            self.robot_controller.limpiar()  # Libera los recursos de la cámara y el puerto serial
            self.robot_controller = None  # Elimina el controlador para reinicializar en iniciar_camara
        self.camara_label.clear()  # Limpia la vista de la cámara

    def update_image(self):
        """Captura un nuevo cuadro de la cámara y lo muestra en la etiqueta de la interfaz."""
        if self.robot_controller:
            qt_image = self.robot_controller.capturar_cuadro()
            if qt_image:
                scaled_image = qt_image.scaled(self.camara_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.camara_label.setPixmap(QPixmap.fromImage(scaled_image))

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
