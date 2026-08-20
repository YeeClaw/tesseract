from typing import Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton


class ThemeToggle(QPushButton):

    change_theme_signal = Signal()

    def __init__(self, current_theme: Literal['dark', 'light']):
        super().__init__("Toggle Theme!")

        self.clicked.connect(self.__on_click)
        self._current_theme: Literal['dark', 'light'] = current_theme


    def __on_click(self) -> None:
        self.change_theme_signal.emit()


    def __set_theme(self) -> None:
        """Apply the stylesheet of the other theme.

        Not built. The main window owns the stylesheet of the application, so
        this method waits for the settings store of M1.
        """
        raise NotImplementedError


    def update_button_state(self, theme: Literal['dark', 'light']) -> None:
        """
        Application calls this to inform the button about the existing state.
        """
        self._current_theme = theme
