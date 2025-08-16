from PySide6.QtWidgets import QMainWindow, QPushButton
from tesseract.utils.helpers import load_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Tesseract - A Minecraft Launcher")
        self.resize(1280, 720)

        theme_toggle = QPushButton("Toggle Theme")
        self.setCentralWidget(theme_toggle)
