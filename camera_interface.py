from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

class CameraWindow(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setWindowTitle("Ventana de Cámara")
        self.setGeometry(100, 100, 800, 600)

        # Layout principal
        layout_principal = QVBoxLayout()

        # Placeholder para el cuadro de la cámara
        self.camara_label = QLabel("Aquí se mostraría la cámara en el robot script")
        layout_principal.addWidget(self.camara_label)

        # Botones de control
        layout_botones = QHBoxLayout()
        regresar_boton = QPushButton("Regresar")
        regresar_boton.clicked.connect(self.regresar)
        detener_boton = QPushButton("Detener Cámara")
        detener_boton.clicked.connect(self.detener_robot_script)

        layout_botones.addWidget(regresar_boton)
        layout_botones.addWidget(detener_boton)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

    def detener_robot_script(self):
        """Método para detener el script del robot enviando señal de cierre."""
        # Aquí podríamos enviar un comando para detener, o terminar el proceso de `robot_control.py` si es necesario.
        print("Deteniendo el script del robot (para implementar)")

    def regresar(self):
        """Regresa a la ventana principal."""
        self.stacked_widget.setCurrentIndex(0)
