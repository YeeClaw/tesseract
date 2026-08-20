from PySide6.QtWidgets import QMainWindow, QPushButton

from tesseract.constants import DEFAULT_HEIGHT, DEFAULT_WIDTH


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Tesseract - A Minecraft Launcher")
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        theme_toggle = QPushButton("Toggle Theme")
        self.setCentralWidget(theme_toggle)
