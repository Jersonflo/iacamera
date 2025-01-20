import pyttsx3
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QPainter, QBrush, QColor, QIcon
from robot_control import RobotCameraController
from Gemini import ChatBotApp 
from voice import SpeechRecognizer
import matplotlib.pyplot as plt
import threading
from multiprocessing import Queue
import queue
import psutil




class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventana Principal")
        self.setGeometry(100, 100, 1200, 800)
        
        #verificamos conexion a internet (ethernet o wifi)
        # Devuelve True si alguna interfaz está activa, False en caso contrario
        self.is_connected = any(stats.isup for stats in psutil.net_if_stats().values())
        

        # Inicialización del motor de texto a voz
        self.engine = pyttsx3.init()
        self.reproducir_mensaje_inicial("""Bienvenido al sistema de control y seguimiento visual del robot.""")

        # Cola para pasar las preguntas entre hilos
        self.q = queue.Queue()
        self.plot_queue = queue.Queue()
        
        # Inicializa ChatBotApp y SpeechRecognizer
        self.chatbot_app = ChatBotApp() 
        self.voice_app = SpeechRecognizer()
        
        # Layout principal
        layout_principal = QHBoxLayout()

        # Espaciador en el lado izquierdo
        layout_principal.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))  

        # Fondo de imagen como QLabel
        fondo = QLabel(self)
        fondo.setPixmap(QPixmap("images/fondo.png").scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        fondo.setGeometry(self.rect())
        fondo.setStyleSheet("border: none;")
        fondo.lower()

        # Layout izquierdo (logo y área de cámara)
        layout_izquierdo = QVBoxLayout()

        # Configuración del logo
        self.logo = QLabel()
        pixmap_logo = QPixmap("images/logo.png").scaled(600, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo.setPixmap(pixmap_logo)
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet("background-color: transparent;")
        layout_izquierdo.addWidget(self.logo)

        # Área de visualización de la cámara
        self.camara_label = QLabel()
        self.camara_label.setFixedSize(895, 504)
        self.camara_label.setStyleSheet("background-color: #dcfffe; border-radius: 20px")  
        layout_izquierdo.addWidget(self.camara_label)
        layout_principal.addLayout(layout_izquierdo)

        # Espaciador superior para centrar los botones
        layout_izquierdo.addSpacerItem(QSpacerItem(40, 60, QSizePolicy.Minimum))

        # Layout derecho (botones)
        layout_derecho = QVBoxLayout()

        # Espaciador superior para centrar los botones
        layout_derecho.addSpacerItem(QSpacerItem(20, 120, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Botón de Iniciar
        self.iniciar_boton = QPushButton()
        self.iniciar_boton.setFixedSize(200,160)
        self.iniciar_boton.setIcon(QIcon("images/btniniciar.png"))
        self.iniciar_boton.setIconSize(self.iniciar_boton.size())
        self.iniciar_boton.clicked.connect(self.iniciar_camara)
        self.iniciar_boton.setStyleSheet("background-color: transparent; border: none;")
        layout_derecho.addWidget(self.iniciar_boton)

        # Botón de Detener
        self.detener_boton = QPushButton()  
        self.detener_boton.setFixedSize(200, 160)
        self.detener_boton.setIcon(QIcon("images/btnDetener.png"))
        self.detener_boton.setIconSize(self.detener_boton.size())
        self.detener_boton.clicked.connect(self.detener_camara)
        self.detener_boton.setStyleSheet("background-color: transparent; border: none;")
        layout_derecho.addWidget(self.detener_boton)

        # Botón de Conócenos
        self.conocenos_boton = QPushButton()
        self.conocenos_boton.setFixedSize(200, 160)
        self.conocenos_boton.setIcon(QIcon("images/btnConocenos.png"))
        self.conocenos_boton.setIconSize(self.conocenos_boton.size())
        self.conocenos_boton.clicked.connect(self.mostrar_mensaje_conocenos)
        self.conocenos_boton.setStyleSheet("background-color: transparent; border: none;")
        layout_derecho.addWidget(self.conocenos_boton)

        # Configuración del botón de Ayuda (en la esquina inferior derecha con icono de imagen)
        self.ayuda_boton = QPushButton()
        self.ayuda_boton.setFixedSize(50, 50)  # Tamaño del botón
        self.ayuda_boton.setStyleSheet("border-radius: 20px; background-color: transparent;")  
        self.ayuda_boton.setIcon(QIcon("images/btnAyuda.png"))  
        self.ayuda_boton.setIconSize(self.ayuda_boton.size())  
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
        # Verifica si el controlador del robot ya está inicializado
        if not self.robot_controller:
            # Inicializa el controlador de la cámara y del robot
            self.robot_controller = RobotCameraController(serial_port='COM10')
        
        # Comprueba si hay conexión antes de iniciar la escucha continua de audio
        if self.is_connected:
            self.iniciar_escucha_continua()
        
        # Arranca el temporizador para la cámara
        self.timer.start(30)

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
                # Ajustar el tamaño de la imagen al tamaño de la cámara_label
                scaled_image = qt_image.scaled(self.camara_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

                # Crear un QPixmap redondeado
                rounded_pixmap = QPixmap(self.camara_label.size())
                rounded_pixmap.fill(Qt.transparent)  # Fondo transparente

                # Crear un pintor para aplicar el borde redondeado
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QBrush(scaled_image))
                painter.setPen(Qt.NoPen)

                # Dibujar un rectángulo con bordes redondeados
                radius = 20.1  # Radio de las esquinas redondeadas
                painter.drawRoundedRect(rounded_pixmap.rect(), radius, radius, Qt.AbsoluteSize)
                painter.end()

                # Establecer el QPixmap redondeado en el QLabel
                self.camara_label.setPixmap(rounded_pixmap)

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
        
        
    def graficar_espectrograma(self):
        """Genera un espectrograma del audio extraído desde la cola."""
        print("Tamaño de la cola:", self.plot_queue.qsize())
        if not self.plot_queue.empty():
            # Extraer datos de la cola
            audio_data = self.plot_queue.get()

            with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                framerate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                audio_frames = wav_file.readframes(n_frames)
                audio_samples = np.frombuffer(audio_frames, dtype=np.int16)

                # Configuración del espectrograma
                plt.figure(figsize=(10, 6))
                plt.specgram(audio_samples, Fs=framerate, NFFT=1024, noverlap=512, cmap="viridis")
                plt.title("Espectrograma del audio")
                plt.xlabel("Tiempo (s)")
                plt.ylabel("Frecuencia (Hz)")
                plt.colorbar(label="Intensidad (dB)")
                plt.tight_layout()
                plt.show()
        else:
            print("La cola está vacía. No hay datos de audio para procesar.")

    def iniciar_escucha_continua(self):
        """Inicia la escucha continua de voz en un hilo separado."""
        def escuchar_y_enviar():
            while True:
                
                self.voice_app.escuchar_continuamente()

        threading.Thread(target=escuchar_y_enviar, daemon=True).start()

    def keyPressEvent(self, event):
        """Cierra la ventana y la cámara al presionar la tecla Esc."""
        if event.key() == Qt.Key_Escape:
            self.graficar_espectrograma()
            self.detener_camara()
            self.close()