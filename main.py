import sys
from PyQt5.QtWidgets import QApplication
from interface import MainWindow  

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec_())



