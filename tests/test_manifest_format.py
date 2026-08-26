"""
Make a change to the manifest format a decision.

Rule 1: the frozen example of each format still opens, and keeps its values.
Rule 2: the field set of the current format is written down. A change that the
snapshot does not show is a fault.

`Instance` shows the current format only. #59 lifts an older one.

Author: Claude Code.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tesseract.constants import MANIFEST_FORMAT
from tesseract.core.models import Instance

MANIFEST_ROOT = Path(__file__).resolve().parent/"manifests"

# Each field of format 1, and whether it is necessary. Do not edit a snapshot of a
# format that is not the current one; it records what a migration receives.
FORMAT_1_FIELDS = {
    "id": False,
    "name": True,
    "slug": False,
    "format": False,
    "minecraft_version": True,
    "memory_mb": True,
    "loader": False,
    "loader_version": False,
    "launch_version": False,
    "kind": False,
    "java_path": False,
    "jvm_arguments": False,
    "window_size": False,
    "created_at": False,
    "played_at": False,
}

SNAPSHOTS = {1: FORMAT_1_FIELDS}


def _load(text: str) -> Instance:
    """Give the instance that one manifest holds. This is the seam for #59."""
    return Instance.model_validate_json(text)


def _get_example(format_number: int) -> str:
    """Give the text of the frozen example manifest of one format."""
    return (MANIFEST_ROOT/f"format-{format_number}.json").read_text(encoding="utf-8")


def _get_necessary_fields() -> dict[str, bool]:
    """Give each field of the model, and whether it is necessary."""
    return {name: field.is_required() for name, field in Instance.model_fields.items()}


def test_an_example_exists_for_each_format() -> None:
    """Guard the tests below. A missing example makes a test pass and prove nothing"""
    assert MANIFEST_ROOT.is_dir(), f"no manifest examples at {MANIFEST_ROOT}"

    missing = [
        number
        for number in range(1, MANIFEST_FORMAT + 1)
        if not (MANIFEST_ROOT/f"format-{number}.json").is_file()
    ]

    assert not missing, (
        f"no example manifest for format: {missing}. "
        "Write tests/manifests/format-N.json by hand. Do not generate it."
    )


def test_a_snapshot_exists_for_each_format() -> None:
    """Guard the drift test. A format without a snapshot is a format without a rule"""
    missing = [number for number in range(1, MANIFEST_FORMAT + 1) if number not in SNAPSHOTS]

    assert not missing, (
        f"no field snapshot for format: {missing}. "
        "Add a FORMAT_N_FIELDS constant and list it in SNAPSHOTS."
    )


@pytest.mark.parametrize(
    "format_number",
    [pytest.param(number, id=f"format-{number}") for number in range(1, MANIFEST_FORMAT + 1)]
)
def test_an_example_manifest_still_opens(format_number: int) -> None:
    """Rule 1. Every example that an earlier release wrote must still open"""
    text = _get_example(format_number)

    try:
        instance = _load(text)
    except ValidationError as error:
        pytest.fail(
            f"the example of format {format_number} no longer opens:\n{error}\n"
            "Revert the change, or lift MANIFEST_FORMAT and write the migration (#59)."
        )

    assert instance.format == MANIFEST_FORMAT


def test_the_example_of_format_1_keeps_its_values() -> None:
    """Rule 1. A renamed field still opens, because pydantic drops an unknown name"""
    manifest = json.loads(_get_example(1))
    instance = _load(_get_example(1))

    assert str(instance.id) == manifest["id"]
    assert instance.name == manifest["name"]
    assert instance.slug == manifest["slug"]
    assert instance.minecraft_version == manifest["minecraft_version"]
    assert instance.memory_mb == manifest["memory_mb"]
    assert instance.loader == manifest["loader"]
    assert instance.loader_version == manifest["loader_version"]
    assert instance.launch_version == manifest["launch_version"]
    assert instance.kind == manifest["kind"]
    assert str(instance.java_path) == manifest["java_path"]
    assert instance.jvm_arguments == manifest["jvm_arguments"]
    assert instance.window_size == tuple(manifest["window_size"])
    assert instance.played_at is not None


def test_the_model_agrees_with_the_snapshot() -> None:
    """Rule 2. This does not stop a change. It stops a change that nobody decided"""
    current = _get_necessary_fields()
    snapshot = SNAPSHOTS[MANIFEST_FORMAT]

    added = sorted(set(current) - set(snapshot))
    removed = sorted(set(snapshot) - set(current))
    changed = sorted(
        name for name in set(current) & set(snapshot) if current[name] != snapshot[name]
    )

    assert not (added or removed or changed), (
        f"the model no longer agrees with format {MANIFEST_FORMAT}: "
        f"added={added}, removed={removed}, necessity changed={changed}. "
        f"A new optional field goes in FORMAT_{MANIFEST_FORMAT}_FIELDS as False. "
        "Anything else lifts MANIFEST_FORMAT, and needs a new snapshot, a new frozen "
        "example, and a migration (#59)."
    )
