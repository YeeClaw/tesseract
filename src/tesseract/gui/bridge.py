"""
This module hands each message of Qt (who sends logs to stderr) to structlog instead,
so that the file holds the lines of Qt beside the lines of Tesseract.

The module imports Qt, and it lives beside the GUI for that reason. Nothing
in the core may import it.
"""

import logging
import os
from typing import Final

import structlog
from PySide6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QStyleFactory

# The variable that a desktop sets to choose the widget style of every Qt
# application of the session, such as "kvantum" on a KDE-flavoured session.
STYLE_VARIABLE = "QT_STYLE_OVERRIDE"

# The name that every record of Qt carries, so that a filter reaches them all.
LOGGER_NAME = "qt"

_LEVELS: Final[dict[QtMsgType, int]] = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}

_logger = structlog.get_logger(LOGGER_NAME)


def _to_structlog(mode: QtMsgType, context: QMessageLogContext, message: str) -> None:
    """
    Write one message of Qt as one record of structlog.

    Qt calls this from whichever thread emitted the message, and it aborts the
    process after a fatal one. The body therefore raises nothing: a broken log
    must not take the launcher with it.
    """
    try:
        # A release build of Qt drops the file, the line, and the function, so
        # each of the three joins the record only when it holds something.
        candidates = {
            "qt_category": context.category,
            "qt_file": context.file,
            "qt_line": context.line or None,
            "qt_function": context.function,
        }
        origin = {key: value for key, value in candidates.items() if value}

        _logger.log(_LEVELS.get(mode, logging.WARNING), message, **origin)
    except Exception:  # noqa: BLE001 - see the docstring.
        pass


def install_message_handler() -> None:
    """
    Send every later message of Qt to the log.

    Call this before the QApplication exists. Qt speaks during that
    constructor, and a handler installed after it misses those messages.
    """
    qInstallMessageHandler(_to_structlog)


def drop_unavailable_style_override() -> str | None:
    """
    Unset `QT_STYLE_OVERRIDE` when the Qt of the launcher cannot load it, and
    give the name that was dropped. Give None when nothing was dropped.

    The wheel of PySide6 carries its own copy of Qt, and that copy ships no
    style plugin at all. A style of the session such as Kvantum lives beside
    the Qt of the system, out of its reach. The constructor of QApplication
    then writes a warning on every start, and it falls back to Fusion.

    Tesseract paints itself with its own stylesheet, so the fallback costs the
    look of the launcher nothing. Dropping the variable buys a quiet start and
    one record that says what happened. A copy of Qt that does find the style,
    such as the PySide6 of a distribution, keeps the variable and the style.
    """
    wanted = os.environ.get(STYLE_VARIABLE)
    if not wanted:
        return None

    # Qt matches the name of a style without regard to case.
    available = QStyleFactory.keys()
    if wanted.casefold() in {key.casefold() for key in available}:
        return None

    # Otherwise, what we want simply isn't available.
    del os.environ[STYLE_VARIABLE]
    _logger.info(
        "style override dropped", style=wanted, available=available, variable=STYLE_VARIABLE
    )
    return wanted
