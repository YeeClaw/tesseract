"""
The one place that configures the log of the launcher.

The module imports no Qt. The handler that fills the console of the
application belongs in the bridge module, because that handler touches Qt.
"""

import logging
import logging.handlers
from pathlib import Path

import structlog
from structlog.typing import Processor

LOG_FILE = "tesseract.jsonl"

# How much the file keeps: five files of two megabytes each.
_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 5

# format_exc_info is absent on purpose. ConsoleRenderer formats a traceback
# itself, and the file writes the frames as JSON with its own transformer.
_SHARED: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
]


def console_formatter(colors: bool = True) -> structlog.stdlib.ProcessorFormatter:
    """
    Give a formatter that writes one readable line for a person.

    The console of the application shows no ANSI colour. Give `colors=False`
    for that destination.
    """
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=colors),
        ],
    )


def _file_formatter() -> structlog.stdlib.ProcessorFormatter:
    """
    Give a formatter that writes one JSON object for a machine.

    The transformer writes the frames of a traceback, and no local variable.
    A local variable can hold a token of Microsoft, and a person sends the log
    file with a report of a fault.
    """
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
            ),
            structlog.processors.JSONRenderer(),
        ],
    )


def configure(level: str, log_dir: Path) -> None:
    """
    Send readable records to the terminal and JSON records to a file.

    `level` sets the terminal only. The file always keeps the debug records,
    because a report of a fault needs them.

    Make the directory of the log when it does not exist. Replace every
    handler of the root logger, so that a second call is safe.
    """
    structlog.configure(
        processors=[*_SHARED, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    to_terminal = logging.StreamHandler()
    to_terminal.setLevel(level)
    to_terminal.setFormatter(console_formatter())

    log_dir.mkdir(parents=True, exist_ok=True)
    to_file = logging.handlers.RotatingFileHandler(
        log_dir / LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    to_file.setLevel(logging.DEBUG)
    to_file.setFormatter(_file_formatter())

    # A level on the root logger would hide a debug record from the
    # file as well as from the terminal.
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = [to_terminal, to_file]

    # The library reports every downloaded file at the debug level. INFO keeps
    # the file readable, and it keeps the records of Tesseract visible.
    logging.getLogger("minecraft_launcher_lib").setLevel(logging.INFO)
