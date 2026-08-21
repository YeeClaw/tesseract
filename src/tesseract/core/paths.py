"""
The directories that Tesseract writes into.

platformdirs chooses the correct place on Linux, Windows, and macOS.
Overrides exist mostly for the purposes of testing, but could be useful
for some users as well.

Each function reads the environment when it runs, and not when the module
loads. A test can therefore set the variable after the import.
"""

import os
from pathlib import Path

from platformdirs import user_data_dir

# The variable that moves the data directory. A test sets it. A person can set
# it too, to keep the launcher on another disk.
DATA_DIR_VARIABLE = "TESSERACT_DATA_DIR"

# appauthor=False keeps the name of the author out of the path on Windows.
_APP_NAME = "tesseract"


def data_dir() -> Path:
    """
    Give the directory that holds every file of the launcher.

    Linux: `~/.local/share/tesseract`.
    Windows: `%LOCALAPPDATA%\\tesseract`.
    macOS: `~/Library/Application Support/tesseract`.
    """
    override = os.environ.get(DATA_DIR_VARIABLE)
    if override:
        return Path(override).expanduser()
    return Path(user_data_dir(_APP_NAME, appauthor=False))


def log_dir() -> Path:
    """Give the directory that holds the log files of the launcher."""
    return data_dir()/"logs"
