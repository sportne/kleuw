"""Project level abstractions for Kleuw."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Project"]


@dataclass(slots=True)
class Project:
    """In-memory representation of a Kleuw project file.

    Attributes:
        version: Schema version number. Currently fixed at ``1``.
        files: Mutable sequence of file entry dictionaries mirroring the
            serialized JSON objects.
        links: Mutable sequence of link entry dictionaries.
        metadata: Optional metadata object preserved from the JSON payload.
    """

    version: int = 1
    files: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Project:
        """Create a project instance from a dictionary payload."""

        version = int(payload.get("version", 1))
        files_data = payload.get("files", [])
        links_data = payload.get("links", [])
        metadata = payload.get("metadata")
        return cls(
            version=version,
            files=deepcopy(list(files_data)),
            links=deepcopy(list(links_data)),
            metadata=deepcopy(metadata) if metadata is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy suitable for JSON serialization."""

        payload: dict[str, Any] = {
            "version": self.version,
            "files": deepcopy(self.files),
            "links": deepcopy(self.links),
        }
        if self.metadata is not None:
            payload["metadata"] = deepcopy(self.metadata)
        return payload
