"""
A set of unit tests created to ensure that instance stores are behaving
correctly across implementations.

Each test writes into a temporary directory, and never into the real one.

Author: Opus 5 (Claude Code). A `# author:` comment marks each test that someone else
wrote.
"""

import shutil
from collections.abc import Callable
from pathlib import Path

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


# ===[ROOT]===
def test_missing_root_is_created(tmp_path: Path) -> None:
    """A missing parent must not stop a first start."""
    root = tmp_path/"absent"/"instances"
    assert not root.exists()

    InstanceStore(root)

    assert root.is_dir()


def test_empty_root_opens(tmp_path: Path) -> None:
    root = tmp_path/"instances"
    root.mkdir()

    assert InstanceStore(root).root == root


def test_store_without_root_uses_data_directory(tmp_path: Path) -> None:
    """The fallback must never give the real directory."""
    store = InstanceStore()

    assert store.root == instances_dir()
    assert store.root.is_dir()
    assert tmp_path in store.root.parents


# ===[CREATE, STRUCTURE]===
def test_create_gives_directory_structure(store: InstanceStore) -> None:
    """#7 names the three parts."""
    instance = get_minimal_instance()

    store.create_instance(instance)

    directory = store.root/instance.slug
    assert (directory/"instance.json").is_file()
    assert (directory/"minecraft").is_dir()
    assert (directory/"logs").is_dir()


def test_create_gives_id_of_instance(store: InstanceStore) -> None:
    instance = get_minimal_instance()

    assert store.create_instance(instance) == instance.id


def test_manifest_holds_model(store: InstanceStore) -> None:
    """A full loop through the disk must change no value."""
    instance = get_minimal_instance()

    store.create_instance(instance)

    assert store.read_instance(store.root/instance.slug) == instance


def test_no_temporary_file_stays_on_disk(store: InstanceStore) -> None:
    instance = get_minimal_instance()

    store.create_instance(instance)

    directory = store.root/instance.slug
    assert sorted(item.name for item in directory.iterdir()) == [
        "instance.json", "logs", "minecraft"
    ]


# ===[CREATE, NAME OF DIRECTORY]===
def test_directory_takes_slug(store: InstanceStore) -> None:
    """The slug is the second form of ID."""
    instance = get_minimal_instance(name="Create: Mischief")

    store.create_instance(instance)

    assert instance.slug == "create-mischief"
    assert (store.root/"create-mischief").is_dir()


def test_second_instance_of_one_name_takes_number(store: InstanceStore) -> None:
    """The first instance keeps the plain slug."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert (store.root/"create-mischief").is_dir()
    assert (store.root/"create-mischief-1").is_dir()


def test_model_takes_name_of_directory(store: InstanceStore) -> None:
    """The slug and the directory must agree."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert second.slug == "create-mischief-1"
    assert store.read_instance(store.root/second.slug).slug == second.slug


def test_collision_keeps_first_instance(store: InstanceStore) -> None:
    """A new instance must never write over another one."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert store.read_instance(store.root/"create-mischief").id == first.id


# ===[CREATE, FAULTS]===
def test_one_model_twice_raises(store: InstanceStore) -> None:
    """One ID is one instance."""
    instance = get_minimal_instance()
    store.create_instance(instance)

    with pytest.raises(InstanceError):
        store.create_instance(instance)

    assert len(list(store.root.iterdir())) == 1


def test_full_namespace_raises(store: InstanceStore) -> None:
    instance = get_minimal_instance(name="test")
    (store.root/"test").mkdir()
    for number in range(1, 100):
        (store.root/f"test-{number}").mkdir()

    with pytest.raises(InstanceError, match="no free directory"):
        store.create_instance(instance)


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
def test_read_gives_what_create_wrote(store: InstanceStore) -> None:
    instance = get_minimal_instance(name="Create: Mischief")
    store.create_instance(instance)

    assert store.read_instance(store.root/instance.slug) == instance


def test_missing_directory_raises(store: InstanceStore) -> None:
    with pytest.raises(InstanceError, match="missing manifest"):
        store.read_instance(store.root/"absent")


def test_missing_manifest_raises(store: InstanceStore) -> None:
    """A directory is not an instance until it holds a manifest."""
    _no_manifest(store.root/"damaged")

    with pytest.raises(InstanceError, match="missing manifest"):
        store.read_instance(store.root/"damaged")


def test_manifest_that_is_not_json_raises(store: InstanceStore) -> None:
    _manifest_that_is_not_json(store.root/"damaged")

    with pytest.raises(InstanceError, match="malformed manifest"):
        store.read_instance(store.root/"damaged")


def test_manifest_that_is_not_utf8_raises(store: InstanceStore) -> None:
    """A manifest written on another platform must not give a raw decode fault."""
    _manifest_that_is_not_utf8(store.root/"damaged")

    with pytest.raises(InstanceError, match="utf-8"):
        store.read_instance(store.root/"damaged")


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


# ===[REFRESH]===
def test_refresh_finds_instance_of_another_store(tmp_path: Path) -> None:
    """A second store must hold what the first one wrote."""
    root = tmp_path/"instances"
    instance = get_minimal_instance()
    InstanceStore(root).create_instance(instance)

    reopened = InstanceStore(root)

    with pytest.raises(InstanceError):
        reopened.create_instance(instance)


def test_refresh_drops_deleted_instance(store: InstanceStore) -> None:
    """A person can delete a directory, and the store must agree."""
    instance = get_minimal_instance()
    store.create_instance(instance)
    shutil.rmtree(store.root/instance.slug)

    store.refresh()

    assert store.create_instance(instance) == instance.id


def test_refresh_ignores_file_in_root(store: InstanceStore) -> None:
    (store.root/"notes.txt").write_text("hello", encoding="utf-8")

    store.refresh()

    assert store.skipped == []


def test_skipped_is_empty_when_every_instance_opens(store: InstanceStore) -> None:
    store.create_instance(get_minimal_instance(name="one"))
    store.create_instance(get_minimal_instance(name="two"))

    store.refresh()

    assert store.skipped == []


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


# author: austin
# TODO(austin): write this test, then delete the skip and this comment
@pytest.mark.skip(reason="stub: austin writes this one")
def test_directory_of_newer_format_raises(store: InstanceStore) -> None:
    """A manifest of a format that this release cannot read must not open."""
    raise NotImplementedError


# author: austin
# TODO(austin): write this test, then delete the skip and this comment
@pytest.mark.skip(reason="stub: austin writes this one")
def test_skipped_names_every_damaged_directory(store: InstanceStore) -> None:
    """Rule 6. A person must be able to learn which instances did not open."""
    raise NotImplementedError
