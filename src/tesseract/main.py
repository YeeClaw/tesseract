import argparse
import sys

import structlog
from PySide6.QtWidgets import QApplication

from tesseract.core import logs, paths
from tesseract.gui.windows import MainWindow
from tesseract.utils.helpers import load_stylesheet

logger = structlog.get_logger(__name__)


def init_app() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Tesseract")

    dark_theme = load_stylesheet("dark.qss")

    window = MainWindow()
    app.setStyleSheet(dark_theme)

    window.show()

    logger.info("main loop starts", theme="dark")
    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A feature rich, modern, and open source Minecraft launcher"
    )
    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level of the terminal (default: INFO)"
    )
    args = parser.parse_args()

    # The level applies to the terminal only. The file keeps every record.
    logs.configure(level=args.log_level, log_dir=paths.log_dir())

    init_app()


if __name__ == "__main__":
    main()
