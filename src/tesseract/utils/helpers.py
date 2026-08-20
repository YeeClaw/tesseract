"""Small functions that more than one module needs."""

from importlib.resources import files

# The anchor is the package, and not a directory of the checkout. The
# stylesheets are data files inside the package, so importlib.resources finds
# them in an installed wheel and in a source tree both.
_STYLES = ("resources", "styles")


def load_stylesheet(filename: str) -> str:
    """Read one Qt stylesheet from the package and give its text.

    Raise FileNotFoundError when the package holds no such stylesheet.
    """
    return files("tesseract").joinpath(*_STYLES, filename).read_text(encoding="utf-8")
