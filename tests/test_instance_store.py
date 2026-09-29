"""
A set of unit tests created to ensure that instance stores are behaving
correctly across implementations.

Each test writes into a temporary directory, and never into the real one.
"""

import contextlib
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from builders import get_minimal_instance
from tesseract.core.instances import InstanceError, InstanceStore
from tesseract.core.paths import instances_dir


@pytest.fixture
def store(tmp_path: Path) -> InstanceStore:
    """Give a store that writes into a temporary directory."""
    return InstanceStore(tmp_path/"instances")


# Each function damages one directory in the way that its name says.
def _no_manifest(directory: Path) -> None:
    directory.mkdir()


def _manifest_that_is_not_json(directory: Path) -> None:
    directory.mkdir()
    (directory/"instance.json").write_text("{not json", encoding="utf-8")


def _manifest_that_is_not_utf8(directory: Path) -> None:
    directory.mkdir()
    (directory/"instance.json").write_bytes(b"\xff\xfe{")


def _manifest_that_is_newer(directory: Path) -> None:
    directory.mkdir()

    clean_manifest = get_minimal_instance().model_dump_json()
    manifest_dict = json.loads(clean_manifest)
    manifest_dict["format"] += 1 # Will always be MANIFEST_FORMAT + 1
    dirty_manifest = json.dumps(manifest_dict)

    (directory/"instance.json").write_text(dirty_manifest, encoding="utf-8")


# ===[ROOT]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_missing_root_is_created(tmp_path: Path) -> None:
    """A missing parent must not stop a first start."""
    root = tmp_path/"absent"/"instances"
    assert not root.exists()

    InstanceStore(root)

    assert root.is_dir()


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_empty_root_opens(tmp_path: Path) -> None:
    root = tmp_path/"instances"
    root.mkdir()

    assert InstanceStore(root).root == root


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_store_without_root_uses_data_directory(tmp_path: Path) -> None:
    """The fallback must never give the real directory."""
    store = InstanceStore()

    assert store.root == instances_dir()
    assert store.root.is_dir()
    assert tmp_path in store.root.parents


# ===[CREATE, STRUCTURE]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_create_gives_directory_structure(store: InstanceStore) -> None:
    """#7 names the three parts."""
    instance = get_minimal_instance()

    store.create_instance(instance)

    directory = store.root/instance.slug
    assert (directory/"instance.json").is_file()
    assert (directory/"minecraft").is_dir()
    assert (directory/"logs").is_dir()


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_create_gives_id_of_instance(store: InstanceStore) -> None:
    instance = get_minimal_instance()

    assert store.create_instance(instance) == instance.id


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_manifest_holds_model(store: InstanceStore) -> None:
    """A full loop through the disk must change no value."""
    instance = get_minimal_instance()

    store.create_instance(instance)

    assert store.read_instance(store.root/instance.slug) == instance


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_no_temporary_file_stays_on_disk(store: InstanceStore) -> None:
    instance = get_minimal_instance()

    store.create_instance(instance)

    directory = store.root/instance.slug
    assert sorted(item.name for item in directory.iterdir()) == [
        "instance.json", "logs", "minecraft"
    ]


# ===[CREATE, NAME OF DIRECTORY]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_directory_takes_slug(store: InstanceStore) -> None:
    """The slug is the second form of ID."""
    instance = get_minimal_instance(name="Create: Mischief")

    store.create_instance(instance)

    assert instance.slug == "create-mischief"
    assert (store.root/"create-mischief").is_dir()


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_second_instance_of_one_name_takes_number(store: InstanceStore) -> None:
    """The first instance keeps the plain slug."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert (store.root/"create-mischief").is_dir()
    assert (store.root/"create-mischief-1").is_dir()


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_model_takes_name_of_directory(store: InstanceStore) -> None:
    """The slug and the directory must agree."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert second.slug == "create-mischief-1"
    assert store.read_instance(store.root/second.slug).slug == second.slug


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_collision_keeps_first_instance(store: InstanceStore) -> None:
    """A new instance must never write over another one."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert store.read_instance(store.root/"create-mischief").id == first.id


# ===[CREATE, FAULTS]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_one_model_twice_raises(store: InstanceStore) -> None:
    """One ID is one instance."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    with pytest.raises(InstanceError):
        store.create_instance(instance)

    assert len(list(store.root.iterdir())) == 1


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_full_namespace_raises(store: InstanceStore) -> None:
    instance = get_minimal_instance(name="test")
    (store.root/"test").mkdir()
    for number in range(1, 100):
        (store.root/f"test-{number}").mkdir()

    with pytest.raises(InstanceError, match="no free directory"):
        store.create_instance(instance)


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_full_namespace_writes_into_no_directory(store: InstanceStore) -> None:
    """The fault above must leave every directory as it was."""
    instance = get_minimal_instance(name="test")
    (store.root/"test").mkdir()
    for number in range(1, 100):
        (store.root/f"test-{number}").mkdir()

    with pytest.raises(InstanceError):
        store.create_instance(instance)

    assert all(not list(item.iterdir()) for item in store.root.iterdir())


# ===[READ]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_read_gives_what_create_wrote(store: InstanceStore) -> None:
    instance = get_minimal_instance(name="Create: Mischief")
    store.create_instance(instance)

    assert store.read_instance(store.root/instance.slug) == instance


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_missing_directory_raises(store: InstanceStore) -> None:
    with pytest.raises(InstanceError, match="missing manifest"):
        store.read_instance(store.root/"absent")


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_missing_manifest_raises(store: InstanceStore) -> None:
    """A directory is not an instance until it holds a manifest."""
    _no_manifest(store.root/"damaged")

    with pytest.raises(InstanceError, match="missing manifest"):
        store.read_instance(store.root/"damaged")


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_manifest_that_is_not_json_raises(store: InstanceStore) -> None:
    _manifest_that_is_not_json(store.root/"damaged")

    with pytest.raises(InstanceError, match="malformed manifest"):
        store.read_instance(store.root/"damaged")


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_manifest_that_is_not_utf8_raises(store: InstanceStore) -> None:
    """A manifest written on another platform must not give a raw decode fault."""
    _manifest_that_is_not_utf8(store.root/"damaged")

    with pytest.raises(InstanceError, match="utf-8"):
        store.read_instance(store.root/"damaged")


# author: Opus 5 (Claude Code) <llm@coltco.net>
@pytest.mark.parametrize(
    "damage",
    [
        pytest.param(_no_manifest, id="no-manifest"),
        pytest.param(_manifest_that_is_not_json, id="not-json"),
        pytest.param(_manifest_that_is_not_utf8, id="not-utf8"),
    ]
)
def test_error_names_manifest(
    store: InstanceStore, damage: Callable[[Path], None]
) -> None:
    """A traceback reaches a person without the log beside it."""
    directory = store.root/"damaged"
    damage(directory)

    with pytest.raises(InstanceError) as error:
        store.read_instance(directory)

    assert str(directory/"instance.json") in str(error.value)


# ===[UPDATE]===
# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_update_writes_new_value_to_disk(store: InstanceStore) -> None:
    instance = get_minimal_instance()
    store.create_instance(instance)

    store.update_instance(instance.id, memory_mb=2048)

    assert store.read_instance(store.root/instance.slug).memory_mb == 2048


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_update_gives_receipt_of_updated_values(store: InstanceStore) -> None:
    instance = get_minimal_instance()
    store.create_instance(instance)

    receipt = store.update_instance(instance.id, memory_mb=2048, name="renamed")

    assert receipt.updated == {"memory_mb": 2048, "name": "renamed"}
    assert receipt.denied == []


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_receipt_holds_coerced_value(store: InstanceStore) -> None:
    """The receipt holds what the value became, not what was sent."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    receipt = store.update_instance(instance.id, played_at="2026-09-01T12:00:00Z")

    assert receipt.updated["played_at"] == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_update_leaves_no_temporary_file(store: InstanceStore) -> None:
    instance = get_minimal_instance()
    store.create_instance(instance)

    store.update_instance(instance.id, memory_mb=2048)

    directory = store.root/instance.slug
    assert sorted(item.name for item in directory.iterdir()) == [
        "instance.json", "logs", "minecraft"
    ]


# author: Austin Colt <colt.austin@coltco.net>
def test_second_update_builds_on_first(store: InstanceStore) -> None:
    """The store must hold the updated model without a refresh."""
    instance = get_minimal_instance()
    id = store.create_instance(instance)

    store.update_instance(id, name="New Name")
    store.update_instance(id, memory_mb=2048)

    updated_instance = store.read_instance(store.root/instance.slug)

    assert updated_instance.name == "New Name"
    assert updated_instance.memory_mb == 2048


# ===[UPDATE, DENIED]===
# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_denied_key_lands_in_receipt(store: InstanceStore) -> None:
    instance = get_minimal_instance()
    store.create_instance(instance)

    receipt = store.update_instance(instance.id, slug="new-slug")

    assert receipt.denied == ["slug"]
    assert receipt.updated == {}


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_denied_key_changes_nothing_on_disk(store: InstanceStore) -> None:
    """The slug and the directory must stay in agreement."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    store.update_instance(instance.id, slug="new-slug")

    assert store.read_instance(store.root/instance.slug).slug == instance.slug


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_mixed_update_applies_allowed_part(store: InstanceStore) -> None:
    """One denied key must not stop the other changes."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    receipt = store.update_instance(instance.id, slug="new-slug", memory_mb=2048)

    assert receipt.denied == ["slug"]
    assert receipt.updated == {"memory_mb": 2048}


# ===[UPDATE, FAULTS]===
# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_update_of_unknown_id_raises(store: InstanceStore) -> None:
    with pytest.raises(InstanceError, match="no instance"):
        store.update_instance(uuid4(), memory_mb=2048)


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_unknown_key_raises(store: InstanceStore) -> None:
    """A typo must not pass in silence."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    with pytest.raises(InstanceError, match="invalid"):
        store.update_instance(instance.id, memory_mib=2048)


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_invalid_value_raises(store: InstanceStore) -> None:
    instance = get_minimal_instance()
    store.create_instance(instance)

    with pytest.raises(InstanceError, match="invalid"):
        store.update_instance(instance.id, memory_mb=256)


# author: Fable 5 (Claude Code) <llm@coltco.net>
def test_loader_version_without_loader_raises(store: InstanceStore) -> None:
    """A cross-field rule must hold through an update."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    with pytest.raises(InstanceError):
        store.update_instance(instance.id, loader_version="21.1.248")


# author: Austin Colt <colt.austin@coltco.net>
def test_failed_update_leaves_manifest_as_it_was(store: InstanceStore) -> None:
    """A fault must change nothing on disk."""
    instance = get_minimal_instance()
    id = store.create_instance(instance)

    # I'm supressing here instead of using `pytest.raises` as to drive in the semantic meaning
    # of this unit test. `pytest.raises` is an assertion about the test. We don't care about
    # the exception here, we only care about the bad update and want to validate as such.
    with contextlib.suppress(InstanceError):
        # This is a bad change; you cannot have negative RAM (and pydantic will let you know!).
        store.update_instance(id, memory_mb=-1)

    from_store = store.read_instance(store.root/instance.slug)
    assert from_store == instance


# ===[REFRESH]===
# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_refresh_finds_instance_of_another_store(tmp_path: Path) -> None:
    """A second store must hold what the first one wrote."""
    root = tmp_path/"instances"
    instance = get_minimal_instance()
    InstanceStore(root).create_instance(instance)

    reopened = InstanceStore(root)

    with pytest.raises(InstanceError):
        reopened.create_instance(instance)


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_refresh_drops_deleted_instance(store: InstanceStore) -> None:
    """A person can delete a directory, and the store must agree."""
    instance = get_minimal_instance()
    store.create_instance(instance)
    shutil.rmtree(store.root/instance.slug)

    store.refresh()

    assert store.create_instance(instance) == instance.id


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_refresh_ignores_file_in_root(store: InstanceStore) -> None:
    (store.root/"notes.txt").write_text("hello", encoding="utf-8")

    store.refresh()

    assert store.skipped == []


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_skipped_is_empty_when_every_instance_opens(store: InstanceStore) -> None:
    store.create_instance(get_minimal_instance(name="one"))
    store.create_instance(get_minimal_instance(name="two"))

    store.refresh()

    assert store.skipped == []


# author: Opus 5 (Claude Code) <llm@coltco.net>
def test_refresh_clears_skipped_after_repair(store: InstanceStore) -> None:
    """A repaired instance must leave the list of skipped directories."""
    damaged = store.root/"damaged"
    _manifest_that_is_not_json(damaged)
    store.refresh()
    assert store.skipped == [damaged]

    (damaged/"instance.json").write_text(
        get_minimal_instance().model_dump_json(), encoding="utf-8"
    )
    store.refresh()

    assert store.skipped == []


# author: austin <colt.austin@coltco.net>
def test_directory_of_newer_format_raises(store: InstanceStore) -> None:
    """A manifest of a format that this release cannot read must not open."""
    _manifest_that_is_newer(store.root/"newer")
    with pytest.raises(InstanceError, match="update tesseract"):
        store.read_instance(store.root/"newer")


# author: austin <colt.austin@coltco.net>
def test_skipped_names_every_damaged_directory(store: InstanceStore) -> None:
    """A person must be able to learn which instances did not open."""
    # Broken manifests
    _manifest_that_is_not_json(store.root/"not-json")
    _manifest_that_is_not_utf8(store.root/"not-encoded-right")
    _manifest_that_is_newer(store.root/"too-new")

    # Good manifest
    instance = get_minimal_instance()
    store.create_instance(instance)

    store.refresh()

    assert sorted(store.skipped) == sorted([
        store.root/"not-json",
        store.root/"not-encoded-right",
        store.root/"too-new",
    ])
