"""
The tests of the log configuration.

Each test writes into a temporary directory. The fixture puts back the
handlers of the root logger and the defaults of structlog, so that one test
cannot change the log of the next test.
"""

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from tesseract.core import logs


@pytest.fixture(autouse=True)
def restore_the_log() -> Iterator[None]:
    """Give each test the log configuration that it found."""
    # SETUP
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level

    yield # TEST

    # TEARDOWN
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


def test_configure_makes_directory(tmp_path: Path) -> None:
    log_dir = tmp_path/"one"/"two"

    logs.configure(level="INFO", log_dir=log_dir)

    assert (log_dir/logs.LOG_FILE).is_file()


def test_file_holds_keywords_of_event(tmp_path: Path) -> None:
    logs.configure(level="INFO", log_dir=tmp_path)

    structlog.get_logger("tesseract.test").info(
        "install finished", instance="survival-1215", version="1.21.4"
    )

    event = _read_events(tmp_path)[-1]
    assert event["event"] == "install finished"
    assert event["instance"] == "survival-1215"
    assert event["version"] == "1.21.4"
    assert event["level"] == "info"
    assert event["logger"] == "tesseract.test"
    assert "timestamp" in event


def test_file_keeps_record_that_terminal_hides(tmp_path: Path) -> None:
    """The level of the terminal must not reach the file."""
    logs.configure(level="ERROR", log_dir=tmp_path)

    structlog.get_logger("tesseract.test").debug("a quiet record")

    assert [e["event"] for e in _read_events(tmp_path)] == ["a quiet record"]


def test_record_of_stdlib_gets_same_fields(tmp_path: Path) -> None:
    """A module that knows nothing of structlog still writes JSON."""
    logs.configure(level="INFO", log_dir=tmp_path)

    logging.getLogger("some.library").warning("the disk is nearly full")

    event = _read_events(tmp_path)[-1]
    assert event["event"] == "the disk is nearly full"
    assert event["level"] == "warning"
    assert event["logger"] == "some.library"


def test_file_holds_frames_of_exception(tmp_path: Path) -> None:
    logs.configure(level="INFO", log_dir=tmp_path)

    try:
        raise ValueError("no such version")
    except ValueError:
        structlog.get_logger("tesseract.test").exception("install failed")

    frames = _read_events(tmp_path)[-1]["exception"]
    assert isinstance(frames, list)
    assert frames[0]["exc_type"] == "ValueError"
    # A local variable can hold a secret, so the file must hold none.
    assert "locals" not in frames[0]["frames"][0]


def test_library_stays_at_info(tmp_path: Path) -> None:
    """The debug records of the library MUST hide the rest."""
    logs.configure(level="DEBUG", log_dir=tmp_path)

    logging.getLogger("minecraft_launcher_lib").debug("downloaded one file")

    assert _read_events(tmp_path) == []


def test_console_formatter_writes_readable_line(tmp_path: Path) -> None:
    logs.configure(level="INFO", log_dir=tmp_path)
    record = logging.getLogger().makeRecord(
        "tesseract.test", logging.INFO, __file__, 1, "the window opens", (), None
    )

    line = logs.console_formatter(colors=False).format(record)

    assert "the window opens" in line
    assert "\x1b[" not in line
