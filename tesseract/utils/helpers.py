import os
from tesseract.utils.paths import STYLES_DIR


def load_stylesheet(filename: str) -> str:
    absolute_path = os.path.join(STYLES_DIR, filename)
    with open(absolute_path, "r") as file:
        return file.read()
