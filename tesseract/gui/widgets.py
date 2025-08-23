from typing import Literal
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton
from tesseract.utils.helpers import load_stylesheet


class ThemeToggle(QPushButton):

    change_theme_signal = Signal()

    def __init__(self, current_theme: Literal['dark', 'light']):
        super().__init__("Toggle Theme!")

        self.clicked.connect(self.__on_click)
        self._current_theme: Literal['dark', 'light'] = current_theme


    def __on_click(self) -> None:
        self.change_theme_signal.emit()


    def __set_theme(self):
        dark = load_stylesheet("dark.qss")
        light = load_stylesheet("light.qss")

        pass


    def update_button_state(self, theme: Literal['dark', 'light']) -> None:
        """
        Application calls this to inform the button about the existing state.
        """
        self._current_theme = theme
