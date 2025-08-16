import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from tesseract.gui.windows import MainWindow

logger = logging.getLogger(__name__)


def init_app() -> None:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    logger.info(f"Starting main loop!")
    sys.exit(app.exec())


def main():
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

    # I don't fully understand the nuance behind how logging works.
    # If the logger is defined at the top level, how does this work?
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    init_app()


if __name__ == "__main__":
    main()
