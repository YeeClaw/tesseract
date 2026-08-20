import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from tesseract.gui.windows import MainWindow
from tesseract.utils.helpers import load_stylesheet

logger = logging.getLogger(__name__)


def init_app() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Tesseract")

    dark_theme = load_stylesheet("dark.qss")

    window = MainWindow()
    app.setStyleSheet(dark_theme)

    window.show()

    logger.info("Starting main loop!")
    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A lightweight feature rich Minecraft launcher"
    )
    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level for the launcher (default: INFO)"
    )
    args = parser.parse_args()

    # A logger at the top level of a module only names itself. It holds no
    # level and no format of its own. basicConfig gives those to the root
    # logger, and every named logger sends its records up to the root.
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    init_app()


if __name__ == "__main__":
    main()
