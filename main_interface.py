import sys
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QStackedWidget
from camera_interface import CameraWindow

class MainWindow(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setWindowTitle("Ventana Principal")
        self.setGeometry(100, 100, 800, 600)

        layout_principal = QHBoxLayout()

        # Cuadro de texto de introducción
        introduccion_label = QTextEdit("Este es un proyecto de seguimiento visual para un robot...")
        introduccion_label.setReadOnly(True)
        layout_principal.addWidget(introduccion_label)

        # Sección de botones y logo
        layout_derecho = QVBoxLayout()

        # Logo (placeholder)
        logo = QLabel("LOGO AQUÍ")
        logo.setAlignment(Qt.AlignCenter)
        layout_derecho.addWidget(logo)

        # Botones
        iniciar_boton = QPushButton("Iniciar")
        iniciar_boton.clicked.connect(self.iniciar_robot_script)  # Conectar al método que ejecuta el script
        conocenos_boton = QPushButton("Conócenos")
        
        layout_derecho.addWidget(iniciar_boton)
        layout_derecho.addWidget(conocenos_boton)
        layout_principal.addLayout(layout_derecho)
        self.setLayout(layout_principal)

    def iniciar_robot_script(self):
        """Método para ejecutar el script del robot en un proceso separado."""
        subprocess.Popen(['python', 'robot_control.py'])  # Ejecuta el script del robot
        self.stacked_widget.setCurrentIndex(1)  # Cambia a la ventana de cámara

# Clase principal que maneja el cambio de ventanas
class RobotApp(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.main_window = MainWindow(self)
        self.camera_window = CameraWindow(self)

        # Añadir ventanas al stack de ventanas
        self.addWidget(self.main_window)
        self.addWidget(self.camera_window)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = RobotApp()
    ventana.show()
    sys.exit(app.exec_())
