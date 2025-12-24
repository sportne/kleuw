"""Core data models for Kleuw.

The dataclasses defined in this module model the main entities described in
``spec/kleuw_schema.md``.  They intentionally mirror the JSON representation so
that higher level components can validate and transform schema compliant data.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "HashDigest",
    "RegionHash",
    "LineSpan",
    "Target",
    "LinkType",
    "Link",
    "FileEntry",
]


class LinkType(str, Enum):
    """Enumerates the supported relationship types for links."""

    REFERS_TO = "refers_to"
    DEFINES = "defines"
    DECLARES = "declares"
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DEPENDS_ON = "depends_on"
    DUPLICATES = "duplicates"
    MENTIONS = "mentions"
    FIXES = "fixes"
    BLOCKS = "blocks"
    DERIVES_FROM = "derives_from"
    VERIFIES = "verifies"
    BUILDS = "builds"
    DOCUMENTS = "documents"
    RELATES_TO = "relates_to"


@dataclass(frozen=True, slots=True)
class HashDigest:
    """Represents a hash digest.

    Attributes:
        algo: Name of the hashing algorithm used to compute ``value``.
        value: Hex encoded digest string.
    """

    algo: str
    value: str

    def __post_init__(self) -> None:  # pragma: no cover - trivial branchless
        if not self.algo:
            raise ValueError("Hash algorithm must be a non-empty string.")
        if not self.value:
            raise ValueError("Hash value must be a non-empty string.")
        if any(ch not in "0123456789abcdefABCDEF" for ch in self.value):
            raise ValueError("Hash value must be hexadecimal.")


@dataclass(frozen=True, slots=True)
class RegionHash(HashDigest):
    """Hash digest describing a source or destination region."""

    def to_dict(self) -> dict[str, str]:
        """Return a dictionary representation of the region hash."""
        return {"algo": self.algo, "value": self.value}


@dataclass(frozen=True, slots=True)
class LineSpan:
    """Inclusive 1-based line span.

    Attributes:
        start: First line in the span (1-based).
        end: Last line in the span. When omitted, the span refers to ``start``
            only.
    """

    start: int
    end: int | None = None

    def __post_init__(self) -> None:
        if self.start < 1:
            raise ValueError("Line span start must be >= 1.")
        if self.end is not None and self.end < self.start:
            raise ValueError("Line span end must be >= start.")

    @property
    def resolved_end(self) -> int:
        """Return the effective end of the span."""

        return self.end if self.end is not None else self.start

    def to_dict(self) -> dict[str, int | None]:
        """Return a dictionary representation of the line span."""
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True, slots=True)
class Target:
    """Target location for a link endpoint.

    Exactly one of ``file_id`` or ``path`` must be supplied.

    Attributes:
        file_id: Identifier referencing a file entry.
        path: Filesystem path used when ``file_id`` is unavailable.
        lines: Optional line span for the region of interest.
        region_hash: Optional region hash associated with the span.
    """

    file_id: str | None = None
    path: str | None = None
    lines: LineSpan | None = None
    region_hash: RegionHash | None = None

    def __post_init__(self) -> None:
        if (self.file_id is None) == (self.path is None):
            raise ValueError("Exactly one of file_id or path must be provided.")
        if self.file_id is not None and not self.file_id:
            raise ValueError("file_id must be a non-empty string when provided.")
        if self.path is not None and not self.path:
            raise ValueError("path must be a non-empty string when provided.")

    def to_dict(self) -> dict[str, object]:
        """Return a dictionary representation of the target."""
        data: dict[str, object] = {}
        if self.file_id is not None:
            data["file_id"] = self.file_id
        if self.path is not None:
            data["path"] = self.path
        if self.lines is not None:
            data["lines"] = self.lines.to_dict()
        if self.region_hash is not None:
            data["region_hash"] = self.region_hash.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class Link:
    """Relationship between two targets."""

    id: str
    type: LinkType
    src: Target
    dst: Target
    directed: bool = True
    created: str | None = None
    author: str | None = None
    tags: Sequence[str] = field(default_factory=tuple)
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Link id must be a non-empty string.")
        if isinstance(self.type, str):
            object.__setattr__(self, "type", LinkType(self.type))
        if isinstance(self.tags, str):
            raise ValueError("Tags must be provided as an iterable of strings.")
        if isinstance(self.tags, Iterable) and not isinstance(self.tags, tuple):
            object.__setattr__(self, "tags", tuple(self.tags))
        if any(
            not isinstance(tag, str) or not tag or tag.isspace() for tag in self.tags
        ):
            raise ValueError(
                "Tags must be non-empty and contain no whitespace-only values."
            )

    def to_dict(self) -> dict[str, object]:
        """Return a dictionary representation of the link."""
        data: dict[str, object] = {
            "id": self.id,
            "type": self.type.value,
            "src": self.src.to_dict(),
            "dst": self.dst.to_dict(),
        }
        if not self.directed:
            data["directed"] = self.directed
        if self.created is not None:
            data["created"] = self.created
        if self.author is not None:
            data["author"] = self.author
        if self.tags:
            data["tags"] = self.tags
        if self.note is not None:
            data["note"] = self.note
        return data


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Metadata describing a known file in the project."""

    id: str
    path: str
    hash: HashDigest | None = None
    lang: str | None = None
    note: str | None = None
    aliases: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("File id must be a non-empty string.")
        if not self.path:
            raise ValueError("File path must be a non-empty string.")
        if isinstance(self.aliases, str):
            raise ValueError("Aliases must be provided as an iterable of strings.")
        if isinstance(self.aliases, Iterable) and not isinstance(self.aliases, tuple):
            object.__setattr__(self, "aliases", tuple(self.aliases))
        if any(not isinstance(alias, str) or not alias for alias in self.aliases):
            raise ValueError("Aliases must be non-empty strings.")
