"""
Contains shared pydantic models.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator

from tesseract.constants import MANIFEST_FORMAT

WindowSize = tuple[
    Annotated[int, Field(ge=640)], # X
    Annotated[int, Field(ge=320)]  # Y
]


class Instance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4 = Field(default_factory=uuid4)
    name: str
    slug: str = ""
    format: int = Field(ge=1, default=MANIFEST_FORMAT)
    minecraft_version: str
    memory_mb: int = Field(ge=(512))
    loader: Literal["forge", "neoforge", "fabric", "quilt"]|None = None
    loader_version: str|None = None
    launch_version: str = ""
    kind: Literal["client", "server"] = "client"
    java_path: Path|None = None
    jvm_arguments: list[str] = Field(default_factory=list) # Should make its own model when needed
    window_size: WindowSize|None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    played_at: datetime|None = None


    @property
    def is_server(self) -> bool:
        return self.kind == "server"

    @property
    def is_modded(self) -> bool:
        return self.loader is not None


    @field_validator("format")
    @classmethod
    def validate_format(cls, value: int) -> int:
        if value > MANIFEST_FORMAT:
            raise ValueError("Given manifest is newer than expected; please update tesseract")
        return value

    @model_validator(mode="after")
    def validate_version_has_loader(self) -> Self:
        if self.loader_version and not self.loader:
            raise ValueError("Cannot have a loader version without a loader")
        return self

    @model_validator(mode="after")
    def populate_fallbacks(self) -> Self:
        if not self.launch_version:
            self.launch_version = self.minecraft_version

        if not self.slug:
            slug = self.name.lower().strip()
            slug = re.sub(r"[^\w\s-]", " ", slug) # Replace non words, non spaces, and non hyphens
            slug = re.sub(r"[-\s_]+", "-", slug)  # Replace whitespace and hyphens with single hyphen
            slug = slug.strip("-_")

            if not slug:
                slug = str(self.id)

            self.slug = slug

        return self
