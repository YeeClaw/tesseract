"""
The logic behind how instances are managed in the pack.

Each instance lives under `instances/` and has 2 forms of ID. The UUID, and the
slug/name.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import structlog

from tesseract.core.models import Instance
from tesseract.core.paths import instances_dir

log = structlog.get_logger(__name__)


class InstanceError(Exception):
    """An operation on an instance did not succeed."""


@dataclass
class _DiskInstance:
    path: Path
    instance: Instance


class InstanceStore:
    """
    An instance store is responsible for managing all instances on disk.

    This includes basic CRUD operations in addition to reading existing
    instances at the appropriate directory.
    """
    @property
    def root(self) -> Path:
        if self._root is None:
            return instances_dir()
        else:
            return self._root

    def __init__(self, root: Path|None = None):
        self._root = root
        self._store: dict[UUID, _DiskInstance] = {}

        if not self.root.exists():
            log.info("instances directory not found...creating instead")
            self.root.mkdir(parents=True)

        self.refresh()


    # ===[PUBLIC METHODS]===
    def create_instance(self, instance: Instance) -> UUID:
        """
        Create a tracked and managed instance on disk and add it to the store.

        Args:
            instance: Pydantic model of an instance to create on disk.
        Raises:
            InstanceError: When an instance's root cannot otherwise be created.
        """
        if instance.id in self._store:
            raise InstanceError("cannot create duplicate instance from model")

        # Prepare instance root
        for attempt in range(100):
            name = instance.slug if attempt == 0 else f"{instance.slug}-{attempt}"
            instance_root = self.root/name
            try:
                instance_root.mkdir()
                break
            except FileExistsError:
                continue
        else:
            raise InstanceError(f"no free directory for the slug {instance.slug!r}")
        instance.slug = name

        # Create instance structure
        minecraft = instance_root/"minecraft"
        logs      = instance_root/"logs"

        minecraft.mkdir()
        logs.mkdir()

        manifest = instance_root/"instance.json"
        tmp_file = instance_root/"instance.json.tmp"

        tmp_file.write_text(instance.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_file, manifest)

        # Clean up
        self._store[instance.id] = _DiskInstance(path=instance_root, instance=instance)
        return instance.id


    def read_instance(self, path: Path) -> Instance:
        raise NotImplementedError


    def update_instance(self, id: UUID) -> dict[str, object]:
        raise NotImplementedError


    def delete_instance(self, id: UUID) -> None:
        raise NotImplementedError


    def refresh(self) -> None:
        local_store = {}
        for item in self.root.iterdir():
            if item.is_dir():
                try:
                    instance = self.read_instance(item)
                    local_store[instance.id] = _DiskInstance(path=item, instance=instance)
                except InstanceError:
                    log.debug("unable to read an instance", path=str(item))
                    continue
        self._store = local_store


    def duplicate_instance(self) -> UUID:
        raise NotImplementedError


    def get_instance_directory(self, instance: Instance) -> Path:
        raise NotImplementedError

    # ===[PRIVATE HELPERS]===
