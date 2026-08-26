"""
The tests of the bridge between Qt and the log.

Each test writes into a temporary directory, and the fixture puts back the
message handler of Qt and the log configuration afterwards. No test builds a
QApplication, because a message of Qt and the list of the styles both need
none.

Author: Claude Code.
"""

import json
import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from PySide6.QtCore import qDebug, qInstallMessageHandler, qWarning

from tesseract.core import logs
from tesseract.gui import bridge


@pytest.fixture(autouse=True)
def restore_the_log() -> Iterator[None]:
    """Give each test the log configuration and the handler that it found."""
    # SETUP
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level

    yield # TEST

    # TEARDOWN
    qInstallMessageHandler(None)
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers = handlers
    root.setLevel(level)
    structlog.reset_defaults()


def _read_events(log_dir: Path) -> list[dict[str, object]]:
    """Give every JSON object that the file holds, in order."""
    text = (log_dir/logs.LOG_FILE).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_warning_of_qt_reaches_the_file(tmp_path: Path) -> None:
    logs.configure(level="INFO", log_dir=tmp_path)
    bridge.install_message_handler()

    qWarning("invalid style override 'kvantum' passed, ignoring it.")

    event = _read_events(tmp_path)[-1]
    assert event["event"] == "invalid style override 'kvantum' passed, ignoring it."
    assert event["level"] == "warning"
    assert event["logger"] == bridge.LOGGER_NAME
    assert event["qt_category"] == "default"


def test_debug_of_qt_keeps_its_level(tmp_path: Path) -> None:
    """The level of Qt must survive the crossing, and not become a warning."""
    logs.configure(level="INFO", log_dir=tmp_path)
    bridge.install_message_handler()

    qDebug("a detail of the platform")

    assert _read_events(tmp_path)[-1]["level"] == "debug"


class _ExplodingHandler(logging.Handler):
    """A handler of the log that fails the way a full disk fails."""

    def emit(self, record: logging.LogRecord) -> None:
        raise OSError("no space left on device")

    def handleError(self, record: logging.LogRecord) -> None:
        raise OSError("no space left on device")


def test_handler_swallows_a_broken_log(tmp_path: Path) -> None:
    """A message of Qt must never raise into Qt."""
    logs.configure(level="INFO", log_dir=tmp_path)
    bridge.install_message_handler()
    logging.getLogger().handlers = [_ExplodingHandler()]

    qWarning("the disk is nearly full")  # Raises nothing.


def test_unavailable_style_override_goes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    logs.configure(level="INFO", log_dir=tmp_path)
    monkeypatch.setenv(bridge.STYLE_VARIABLE, "kvantum")

    dropped = bridge.drop_unavailable_style_override()

    assert dropped == "kvantum"
    assert os.environ.get(bridge.STYLE_VARIABLE) is None
    event = _read_events(tmp_path)[-1]
    assert event["event"] == "style override dropped"
    assert event["style"] == "kvantum"


def test_available_style_override_stays(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every copy of Qt carries Fusion, and no start may throw it away."""
    monkeypatch.setenv(bridge.STYLE_VARIABLE, "fusion")

    assert bridge.drop_unavailable_style_override() is None
    assert os.environ[bridge.STYLE_VARIABLE] == "fusion"


def test_absent_style_override_is_no_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(bridge.STYLE_VARIABLE, raising=False)

    assert bridge.drop_unavailable_style_override() is None
