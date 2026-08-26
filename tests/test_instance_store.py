"""
A set of unit tests created to ensure that instance stores are behaving
correctly across implementations.

Each test writes into a temporary directory. The store cannot read a manifest
yet, so a test reads one directly, and no test calls `refresh` on a directory
that holds an instance.

Author: Claude Code.
"""

from pathlib import Path

import pytest

from builders import get_minimal_instance
from tesseract.core.instances import InstanceError, InstanceStore
from tesseract.core.models import Instance
from tesseract.core.paths import instances_dir


@pytest.fixture
def store(tmp_path: Path) -> InstanceStore:
    """Give a store that writes into a temporary directory."""
    return InstanceStore(tmp_path/"instances")


def _read_manifest(directory: Path) -> Instance:
    """Give the instance that one directory holds. `read_instance` replaces this."""
    text = (directory/"instance.json").read_text(encoding="utf-8")
    return Instance.model_validate_json(text)


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

    assert _read_manifest(store.root/instance.slug) == instance


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
    assert _read_manifest(store.root/second.slug).slug == second.slug


def test_collision_keeps_first_instance(store: InstanceStore) -> None:
    """A new instance must never write over another one."""
    first = get_minimal_instance(name="Create: Mischief")
    second = get_minimal_instance(name="Create: Mischief")

    store.create_instance(first)
    store.create_instance(second)

    assert _read_manifest(store.root/"create-mischief").id == first.id


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
