"""
Common build functions shared across testing modules.

Each function gives a new model. A test can therefore change what it receives,
and no other test sees that change. Keyword arguments replace a field, so one
builder serves many tests.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from tesseract.constants import MANIFEST_FORMAT
from tesseract.core.models import Instance


# author: austin <colt.austin@coltco.net>
def get_minimal_instance(**overrides: Any) -> Instance:
    """Give an instance that holds the necessary fields only."""
    fields: dict[str, Any] = {
        "name": "test",
        "minecraft_version": "1.21.1",
        "memory_mb": 1024,
    }
    return Instance(**(fields | overrides))


# author: austin <colt.austin@coltco.net>
def get_populated_instance(**overrides: Any) -> Instance:
    """Give an instance that holds a value in every field."""
    fields: dict[str, Any] = {
        "id": uuid4(),
        "name": "Create: Mischief",
        "slug": "create-mischief",
        "format": MANIFEST_FORMAT, # Here for testing compatibility
        "minecraft_version": "1.21.1",
        "memory_mb": 8192,
        "loader": "neoforge",
        "loader_version": "21.1.248",
        "launch_version": "neoforge-21.1.248",
        "kind": "server",
        "java_path": Path("some/java/dir"),
        "jvm_arguments": ["-Xms4G", "-Xmx8G"],
        "window_size": (1280, 720),
        "created_at": datetime(2026, 5, 1, 2, 23, 00, tzinfo=UTC),
        "played_at": datetime(2026, 8, 22, 23, 42, 00, tzinfo=UTC),
    }
    return Instance(**(fields | overrides))
