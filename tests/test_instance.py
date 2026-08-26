"""
Ensure that instances are robust and that drift is caught as soon as possible.

This test modules uses two examples of a manifest--one that uses all default values,
and one that is as specifically designed as possible. Both solve different problems
for testing.

Author: Claude Code.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

import pytest
from pydantic import ValidationError

from builders import get_minimal_instance, get_populated_instance
from tesseract.constants import MANIFEST_FORMAT
from tesseract.core.models import Instance


def _get_minimal_manifest() -> dict[str, object]:
    """Give a minimal manifest as JSON data. A full loop keeps it true to the model."""
    return json.loads(get_minimal_instance().model_dump_json())


# author: austin <colt.austin@coltco.net>
@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            get_minimal_instance,
            id="minimal"
        ),
        pytest.param(
            get_populated_instance,
            id="populated"
        )
    ]
)
def test_model_roundtrip(build: Callable[[], Instance]) -> None:
    """Ensure that a model can be serialized between pydantic and JSON"""
    # The builder runs here, and not at collection. Each test gets its own model.
    instance = build()

    json_instance = instance.model_dump_json()
    instance_from_json = Instance.model_validate_json(json_instance)

    assert instance == instance_from_json


# author: austin <colt.austin@coltco.net>
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("memory_mb", 256, "greater than or equal to 512"),
        ("memory_mb", "duck", "valid integer"),
        ("format", MANIFEST_FORMAT + 1, "please update tesseract"),
        ("format", 0, "greater than or equal to 1"),
        ("kind", "dedicated", "'client' or 'server'"),
        ("loader_version", "21.1.248", "without a loader")
    ]
)
def test_manifest_raises_clear_message(field: str, value: object, message: str) -> None:
    """Ensure that a validation failure gives an explicit message"""
    manifest = _get_minimal_manifest() | {field: value}

    with pytest.raises(ValidationError, match=message):
        Instance.model_validate_json(json.dumps(manifest))


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("name", id="name"),
        pytest.param("minecraft_version", id="minecraft_version"),
        pytest.param("memory_mb", id="memory_mb")
    ]
)
def test_missing_field_raises(field: str) -> None:
    """Ensure that a manifest without a necessary field does not load"""
    manifest = _get_minimal_manifest()
    del manifest[field]

    with pytest.raises(ValidationError, match="Field required"):
        Instance.model_validate_json(json.dumps(manifest))


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param('{"name": "test", "minecraft', id="truncated"),
        pytest.param("[]", id="array"),
        pytest.param("null", id="null")
    ]
)
def test_bad_json_raises_validation_error(text: str) -> None:
    """Ensure that damaged JSON gives a ValidationError, and not a JSON error"""
    with pytest.raises(ValidationError):
        Instance.model_validate_json(text)


def test_unknown_field_is_ignored() -> None:
    """Ensure that an unknown field does not stop a load. The format controls a refusal"""
    manifest = _get_minimal_manifest() | {"future_field": "some value"}

    instance = Instance.model_validate_json(json.dumps(manifest))

    assert not hasattr(instance, "future_field")


def test_current_format_loads() -> None:
    """Ensure that a manifest of the format of this build loads"""
    manifest = _get_minimal_manifest() | {"format": MANIFEST_FORMAT}

    instance = Instance.model_validate_json(json.dumps(manifest))

    assert instance.format == MANIFEST_FORMAT


@pytest.mark.skipif(MANIFEST_FORMAT < 2, reason="There is no older manifest format yet")
def test_older_format_loads() -> None:
    """Ensure that a manifest of an older format loads, because a migration can lift it"""
    manifest = _get_minimal_manifest() | {"format": MANIFEST_FORMAT - 1}

    instance = Instance.model_validate_json(json.dumps(manifest))

    assert instance.format == MANIFEST_FORMAT - 1


def test_absent_launch_version_takes_minecraft_version() -> None:
    """Ensure that a vanilla instance can launch before an installation gives a name"""
    instance = Instance(name="test", minecraft_version="1.21.1", memory_mb=1024)

    assert instance.launch_version == "1.21.1"


def test_given_launch_version_doesnt_change() -> None:
    """Ensure that the name that the loader installation gives is kept"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        loader="fabric",
        launch_version="fabric-loader-0.18.4-1.21.1"
    )

    assert instance.launch_version == "fabric-loader-0.18.4-1.21.1"


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        pytest.param("Survival", "survival", id="simple"),
        pytest.param("   Padded   ", "padded", id="padded"),
        pytest.param("Minecraft 1.21.1", "minecraft-1-21-1", id="dots"),
        pytest.param("My  Server / 2", "my-server-2", id="slash"),
        pytest.param("Café Survival", "café-survival", id="accent"),
        pytest.param("a__b", "a-b", id="underscores"),
        pytest.param(
            "Cobblemon Official Modpack [Fabric]",
            "cobblemon-official-modpack-fabric",
            id="brackets"
        )
    ]
)
def test_name_gives_slug(name: str, slug: str) -> None:
    """Ensure that a name becomes a directory name that a file system accepts"""
    instance = Instance(name=name, minecraft_version="1.21.1", memory_mb=1024)

    assert instance.slug == slug


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("!!!", id="punctuation"),
        pytest.param("   ", id="spaces"),
        pytest.param("---", id="hyphens")
    ]
)
def test_name_without_letters_gives_id_as_slug(name: str) -> None:
    """Ensure that a name that gives an empty slug falls back to the id"""
    instance = Instance(name=name, minecraft_version="1.21.1", memory_mb=1024)

    assert instance.slug == str(instance.id)


def test_stored_slug_doesnt_follow_new_name() -> None:
    """Ensure that a rename does not move the directory of an instance"""
    manifest = _get_minimal_manifest() | {"name": "A New Name"}

    instance = Instance.model_validate_json(json.dumps(manifest))

    assert instance.slug == "test"


def test_loader_without_version_is_valid() -> None:
    """Ensure that an instance can hold a loader before the installation gives a version"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        loader="fabric"
    )

    assert instance.loader_version is None


def test_loader_with_version_is_valid() -> None:
    """Ensure that a fully installed modded instance is valid"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        loader="neoforge",
        loader_version="21.1.248"
    )

    assert instance.loader_version == "21.1.248"


@pytest.mark.parametrize(
    "window_size",
    [
        pytest.param((700, 10), id="short"),
        pytest.param((10, 700), id="narrow"),
        pytest.param((639, 320), id="one_below_the_width"),
        pytest.param((640, 319), id="one_below_the_height")
    ]
)
def test_window_below_minimum_raises(window_size: tuple[int, int]) -> None:
    """Ensure that each axis has its own minimum. A bound on the tuple compares in sequence"""
    with pytest.raises(ValidationError, match="greater than or equal to"):
        Instance(
            name="test",
            minecraft_version="1.21.1",
            memory_mb=1024,
            window_size=window_size
        )


def test_window_at_minimum_is_valid() -> None:
    """Ensure that the smallest permitted window is accepted"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        window_size=(640, 320)
    )

    assert instance.window_size == (640, 320)


def test_absent_window_gives_no_size() -> None:
    """Ensure that an instance without a window size is valid"""
    instance = get_minimal_instance()

    assert instance.window_size is None


@pytest.mark.parametrize(
    ("kind", "is_server"),
    [
        pytest.param("client", False, id="client"),
        pytest.param("server", True, id="server")
    ]
)
def test_kind_gives_is_server(kind: Literal["client", "server"], is_server: bool) -> None:
    """Ensure that the is_server property agrees with the kind"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        kind=kind
    )

    assert instance.is_server is is_server


@pytest.mark.parametrize(
    ("loader", "is_modded"),
    [
        pytest.param(None, False, id="vanilla"),
        pytest.param("fabric", True, id="fabric"),
        pytest.param("neoforge", True, id="neoforge")
    ]
)
def test_loader_gives_is_modded(
    loader: Literal["forge", "neoforge", "fabric", "quilt"]|None,
    is_modded: bool
) -> None:
    """Ensure that the is_modded property agrees with the loader"""
    instance = Instance(
        name="test",
        minecraft_version="1.21.1",
        memory_mb=1024,
        loader=loader
    )

    assert instance.is_modded is is_modded


def test_each_instance_gets_different_id() -> None:
    """Ensure that two instances with the same fields have different identities"""
    first = get_minimal_instance()
    second = get_minimal_instance()

    assert first.id != second.id


def test_minimal_instance_takes_defaults() -> None:
    """Ensure that the default of each optional field does not change without notice"""
    instance = get_minimal_instance()

    assert instance.format == MANIFEST_FORMAT
    assert instance.loader is None
    assert instance.loader_version is None
    assert instance.kind == "client"
    assert instance.java_path is None
    assert instance.jvm_arguments == []
    assert instance.window_size is None
    assert instance.played_at is None


def test_creation_time_has_timezone() -> None:
    """Ensure that the time of creation is not naive, because a naive time sorts wrongly"""
    before = datetime.now(UTC)
    instance = get_minimal_instance()
    after = datetime.now(UTC)

    assert instance.created_at.tzinfo is not None
    assert before <= instance.created_at <= after
