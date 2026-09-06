"""
The logic behind how instances are managed in the pack.

Each instance lives under `instances/` and has 2 forms of ID. The UUID, and the
slug/name.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import structlog
from pydantic import ValidationError

from tesseract.core.models import Instance
from tesseract.core.paths import instances_dir

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)
UPDATE_DENY_LIST = {
    "id",
    "slug",
    "created_at",
    "format"
}


class InstanceError(Exception):
    """An operation on an instance did not succeed."""


@dataclass
class _DiskInstance:
    """Helper for containing and representing instances on the disk

    Attributes:
        path: OS path of the *instance root*.
        instance: In memory model of the instance.
    """
    path:     Path
    instance: Instance


@dataclass
class UpdateReceipt:
    """Helper for handling updated instance transactions.

    Attributes:
        updated: A dictionary containing the updated key and modified value.
        denied: a list of keys which were denied by the store (protected values).
    """
    updated: dict[str, object] = field(default_factory=dict)
    denied:  list[str] = field(default_factory=list)


class InstanceStore:
    """
    An instance store is responsible for managing all instances on disk.

    This includes basic CRUD operations in addition to reading existing
    instances at the appropriate directory.
    """
    @property
    def root(self) -> Path:
        """The instance store root directory"""
        if self._root is None:
            return instances_dir()
        else:
            return self._root

    @property
    def skipped(self) -> list[Path]:
        """A list of skipped directories/files in the store"""
        return self._skipped


    def __init__(self, root: Path|None = None):
        self._root = root
        self._store: dict[UUID, _DiskInstance] = {}
        self._skipped: list[Path] = []

        if not self.root.exists():
            log.info("instances directory not found...creating instead")
            self.root.mkdir(parents=True)

        self.refresh()


    # ===[PUBLIC METHODS]===
    def create_instance(self, instance: Instance) -> UUID:
        """Create a tracked and managed instance on disk and add it to the store.

        Args:
            instance: Pydantic model of an instance to create on disk.

        Raises:
            InstanceError: When an instance's root cannot otherwise be created.

        Returns:
            The UUID of the created instance.
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
        """Given the path to an instance root, return a model of its manifest.

        Args:
            path: A Path pointing at the suggested instance directory.

        Returns:
            An instance Model at the desired root.

        Raises:
            InstanceError: When the location has an invalid manifest or doesn't exist.
        """
        manifest_path = path/"instance.json"
        manifest_log = log.bind(path=str(manifest_path))
        try:
            with open(manifest_path, encoding="utf-8") as manifest:
                contents = manifest.read()
        except OSError as e:
            manifest_log.error("unable to find the requested manifest file")
            raise InstanceError(f"missing manifest file at {manifest_path}") from e
        except UnicodeDecodeError as e:
            manifest_log.error("unable to decode manifest as utf-8")
            raise InstanceError(
                f"provided manifest file ({manifest_path}) is not utf-8 encoded"
            ) from e

        try:
            instance = Instance.model_validate_json(contents)
        except ValidationError as e:
            small_errors = e.errors(include_url=False, include_input=False)
            manifest_log.error(
                "unable to validate manifest",
                errors=small_errors
            )
            raise InstanceError(
                f"found malformed manifest at {str(manifest_path)!r}: "
                f"{small_errors}"
            ) from e

        return instance


    def update_instance(self, id: UUID, **changes) -> UpdateReceipt:
        """Update the manifest within a set of allowed changes.

        Args:
            id: A UUID matching the instance you want to update
            **changes: Any other keyword arguments matching Instance properties

        Returns:
            An UpdateReceipt with updated and denied values.

        Raises:
            InstanceError: when the provided changes do not validate against the model.
        """
        try:
            disc = self._store[id]
        except KeyError:
            raise InstanceError(f"no instance with id '{id}' to update") from None

        instance_root = disc.path
        manifest = instance_root/"instance.json"
        tmp_file = instance_root/"instance.json.tmp"

        receipt = UpdateReceipt()
        for deny_item in UPDATE_DENY_LIST:
            if deny_item in changes:
                log.warning("tried to update a protected value", value=deny_item)
                receipt.denied.append(deny_item)
                del changes[deny_item]

        merged = disc.instance.model_dump() | changes

        # Validate model and handle errors
        try:
            updated_instance = Instance.model_validate(merged)
        except ValidationError as e:
            small_errors = e.errors(include_url=False, include_input=False)
            log.error(
                "unable to validate manifest updates",
                path=str(manifest),
                errors=small_errors
            )
            raise InstanceError(
                f"requested updates to {str(manifest)!r} are invalid: "
                f"{small_errors}"
            ) from e

        # Apply the actual update
        tmp_file.write_text(
            updated_instance.model_dump_json(indent=2),
            encoding="utf-8"
        )
        os.replace(tmp_file, manifest)
        disc.instance = updated_instance

        # Create change receipt
        manifest_dict = updated_instance.model_dump()
        for request in changes:
            receipt.updated[request] = manifest_dict[request]

        return receipt


    def delete_instance(self, id: UUID) -> None:
        raise NotImplementedError


    def refresh(self) -> None:
        local_store: dict[UUID, _DiskInstance] = {}
        skipped: list[Path] = []
        for item in self.root.iterdir():
            if item.is_dir():
                try:
                    instance = self.read_instance(item)
                    local_store[instance.id] = _DiskInstance(path=item, instance=instance)
                except InstanceError:
                    skipped.append(item)
        if skipped:
            log.info(
                "skipped directories when refreshing",
                skipped=[str(item) for item in skipped]
            )

        self._skipped = skipped
        self._store = local_store
        # TODO: Hook this into the UI so that skips aren't (almost) silent


    def duplicate_instance(self) -> UUID:
        raise NotImplementedError


    def get_instance_directory(self, instance: Instance) -> Path:
        raise NotImplementedError

    # ===[PRIVATE HELPERS]===
