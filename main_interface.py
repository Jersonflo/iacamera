import sys
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
        introduccion_label = QTextEdit("Este es un proyecto de seguimiento visual para un robot...")
        introduccion_label.setReadOnly(True)
        layout_principal.addWidget(introduccion_label)

        layout_derecho = QVBoxLayout()
        logo = QLabel("LOGO AQUÍ")
        logo.setAlignment(Qt.AlignCenter)
        layout_derecho.addWidget(logo)

        iniciar_boton = QPushButton("Iniciar")
        iniciar_boton.clicked.connect(self.ir_a_camara)
        conocenos_boton = QPushButton("Conócenos")

        layout_derecho.addWidget(iniciar_boton)
        layout_derecho.addWidget(conocenos_boton)
        layout_principal.addLayout(layout_derecho)
        self.setLayout(layout_principal)

    def ir_a_camara(self):
        """Método para cambiar a la ventana de cámara y empezar la transmisión."""
        self.stacked_widget.setCurrentIndex(1)
        self.stacked_widget.widget(1).iniciar_camara()

class RobotApp(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.main_window = MainWindow(self)
        self.camera_window = CameraWindow(self)

        self.addWidget(self.main_window)
        self.addWidget(self.camera_window)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = RobotApp()
    ventana.show()
    sys.exit(app.exec_())
