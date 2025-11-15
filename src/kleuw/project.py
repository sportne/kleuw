"""Project level abstractions for Kleuw."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

from .model import FileEntry, HashDigest, LineSpan, Link, LinkType, RegionHash, Target

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

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------
    def add_file(self, file_entry: FileEntry | Mapping[str, Any]) -> dict[str, Any]:
        """Add a file entry to the project.

        Args:
            file_entry: Either a :class:`FileEntry` dataclass or a mapping that
                matches the Kleuw schema representation.

        Returns:
            The stored dictionary representing the file entry.

        Raises:
            ValueError: If the file id already exists or the entry is invalid.
        """

        normalized = _normalize_file_entry(file_entry)
        if self.find_file_by_id(normalized["id"]):
            raise ValueError(f"File id '{normalized['id']}' already exists.")
        self.files.append(normalized)
        return normalized

    def find_file_by_id(self, file_id: str) -> dict[str, Any] | None:
        """Return the first file entry that matches ``file_id``."""

        for entry in self.files:
            if isinstance(entry, Mapping) and entry.get("id") == file_id:
                return entry
        return None

    def find_file_by_path(self, path: str) -> dict[str, Any] | None:
        """Return the first file entry with ``path``."""

        for entry in self.files:
            if isinstance(entry, Mapping) and entry.get("path") == path:
                return entry
        return None

    def remove_file(self, file_id: str) -> dict[str, Any] | None:
        """Remove and return a file entry by id."""

        for index, entry in enumerate(self.files):
            if isinstance(entry, Mapping) and entry.get("id") == file_id:
                return self.files.pop(index)
        return None

    # ------------------------------------------------------------------
    # Link helpers
    # ------------------------------------------------------------------
    def add_link(self, link_entry: Link | Mapping[str, Any]) -> dict[str, Any]:
        """Add a link entry to the project.

        Args:
            link_entry: Either a :class:`Link` dataclass or a mapping that
                matches the Kleuw schema representation.

        Returns:
            The stored dictionary representing the link entry.

        Raises:
            ValueError: If the link id already exists, the entry is invalid, or
                it references unknown file identifiers.
        """

        normalized = _normalize_link_entry(link_entry, file_ids=self._file_id_set)
        if self.find_link_by_id(normalized["id"]):
            raise ValueError(f"Link id '{normalized['id']}' already exists.")
        self.links.append(normalized)
        return normalized

    def find_link_by_id(self, link_id: str) -> dict[str, Any] | None:
        """Return the first link entry that matches ``link_id``."""

        for entry in self.links:
            if isinstance(entry, Mapping) and entry.get("id") == link_id:
                return entry
        return None

    def remove_link(self, link_id: str) -> dict[str, Any] | None:
        """Remove and return a link entry by id."""

        for index, entry in enumerate(self.links):
            if isinstance(entry, Mapping) and entry.get("id") == link_id:
                return self.links.pop(index)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @property
    def _file_id_set(self) -> set[str]:
        return {str(entry["id"]) for entry in self.files if isinstance(entry, Mapping)}


TargetKind = Literal["src", "dst"]


def _normalize_file_entry(file_entry: FileEntry | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(file_entry, FileEntry):
        return _file_entry_from_model(file_entry)
    if not isinstance(file_entry, Mapping):
        raise ValueError("File entry must be a mapping or FileEntry instance.")
    return _file_entry_from_mapping(file_entry)


def _file_entry_from_model(file_entry: FileEntry) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": file_entry.id,
        "path": file_entry.path,
    }
    if file_entry.hash is not None:
        result["hash"] = _normalize_hash(file_entry.hash)
    if file_entry.lang is not None:
        result["lang"] = file_entry.lang
    if file_entry.note is not None:
        result["note"] = file_entry.note
    if file_entry.aliases:
        result["aliases"] = [str(alias) for alias in file_entry.aliases]
    return result


def _file_entry_from_mapping(file_entry: Mapping[str, Any]) -> dict[str, Any]:
    raw = deepcopy(dict(file_entry))
    file_id = raw.get("id")
    if not isinstance(file_id, str) or not file_id:
        raise ValueError("File entries must include a non-empty 'id'.")
    path_value = raw.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("File entries must include a non-empty 'path'.")

    result: dict[str, Any] = {"id": file_id, "path": path_value}
    if "hash" in raw:
        result["hash"] = _normalize_hash(raw["hash"])
    if "lang" in raw:
        lang_value = raw["lang"]
        if not isinstance(lang_value, str) or not lang_value:
            raise ValueError("File 'lang' must be a non-empty string.")
        result["lang"] = lang_value
    if "note" in raw:
        note_value = raw["note"]
        if not isinstance(note_value, str):
            raise ValueError("File 'note' must be a string.")
        result["note"] = note_value
    if "aliases" in raw:
        aliases_value = raw["aliases"]
        if isinstance(aliases_value, str):
            raise ValueError("File 'aliases' must be an iterable of strings.")
        try:
            alias_list = [str(alias) for alias in aliases_value]
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValueError("File 'aliases' must be an iterable of strings.") from exc
        if any(not alias for alias in alias_list):
            raise ValueError("File 'aliases' must contain non-empty strings.")
        result["aliases"] = alias_list
    return result


def _normalize_link_entry(
    link_entry: Link | Mapping[str, Any], *, file_ids: set[str]
) -> dict[str, Any]:
    if isinstance(link_entry, Link):
        return _link_entry_from_model(link_entry, file_ids=file_ids)
    if not isinstance(link_entry, Mapping):
        raise ValueError("Link entry must be a mapping or Link instance.")
    return _link_entry_from_mapping(link_entry, file_ids=file_ids)


def _link_entry_from_model(link_entry: Link, *, file_ids: set[str]) -> dict[str, Any]:
    link_type = (
        link_entry.type.value
        if isinstance(link_entry.type, LinkType)
        else str(link_entry.type)
    )
    result: dict[str, Any] = {
        "id": link_entry.id,
        "type": link_type,
        "src": _normalize_target(link_entry.src, kind="src", file_ids=file_ids),
        "dst": _normalize_target(link_entry.dst, kind="dst", file_ids=file_ids),
        "directed": bool(link_entry.directed),
    }
    if link_entry.created is not None:
        result["created"] = link_entry.created
    if link_entry.author is not None:
        result["author"] = link_entry.author
    if link_entry.tags:
        result["tags"] = [str(tag) for tag in link_entry.tags]
    if link_entry.note is not None:
        result["note"] = link_entry.note
    return result


def _link_entry_from_mapping(
    link_entry: Mapping[str, Any], *, file_ids: set[str]
) -> dict[str, Any]:
    raw = deepcopy(dict(link_entry))
    link_id = raw.get("id")
    if not isinstance(link_id, str) or not link_id:
        raise ValueError("Link entries must include a non-empty 'id'.")
    link_type = raw.get("type")
    if isinstance(link_type, LinkType):
        type_value = link_type.value
    elif isinstance(link_type, str):
        type_value = link_type
    else:
        raise ValueError("Link entries must include a non-empty 'type'.")
    if not type_value:
        raise ValueError("Link entries must include a non-empty 'type'.")
    if "src" not in raw or "dst" not in raw:
        raise ValueError("Link entries must include 'src' and 'dst' targets.")

    result: dict[str, Any] = {
        "id": link_id,
        "type": type_value,
        "src": _normalize_target(raw["src"], kind="src", file_ids=file_ids),
        "dst": _normalize_target(raw["dst"], kind="dst", file_ids=file_ids),
        "directed": _normalize_directed(raw.get("directed")),
    }

    if "created" in raw:
        created_value = raw["created"]
        if not isinstance(created_value, str):
            raise ValueError("Link 'created' must be a string.")
        result["created"] = created_value
    if "author" in raw:
        author_value = raw["author"]
        if not isinstance(author_value, str):
            raise ValueError("Link 'author' must be a string.")
        result["author"] = author_value
    if "tags" in raw:
        tags_value = raw["tags"]
        if isinstance(tags_value, str):
            raise ValueError("Link 'tags' must be an iterable of strings.")
        try:
            tags_list = [str(tag) for tag in tags_value]
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValueError("Link 'tags' must be an iterable of strings.") from exc
        if any(not tag or tag.isspace() for tag in tags_list):
            raise ValueError("Link 'tags' must contain non-empty values.")
        result["tags"] = tags_list
    if "note" in raw:
        note_value = raw["note"]
        if not isinstance(note_value, str):
            raise ValueError("Link 'note' must be a string.")
        result["note"] = note_value
    return result


def _normalize_directed(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    raise ValueError("Link 'directed' must be a boolean when provided.")


def _normalize_target(
    target: Target | Mapping[str, Any], *, kind: TargetKind, file_ids: set[str]
) -> dict[str, Any]:
    if isinstance(target, Target):
        if target.file_id is not None and target.file_id not in file_ids:
            raise ValueError(
                f"Target for {kind} references unknown file id '{target.file_id}'."
            )
        return _target_from_model(target, kind=kind)
    if not isinstance(target, Mapping):
        raise ValueError("Target entries must be mappings or Target instances.")
    return _target_from_mapping(target, kind=kind, file_ids=file_ids)


def _target_from_model(target: Target, *, kind: TargetKind) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if target.file_id is not None:
        result["file_id"] = target.file_id
    elif target.path is not None:
        result["path"] = target.path
    if target.lines is not None:
        result["lines"] = _normalize_line_span(target.lines)
    if target.region_hash is not None:
        region_key = "src_region_hash" if kind == "src" else "dst_region_hash"
        result[region_key] = _normalize_hash(target.region_hash)
    return result


def _target_from_mapping(
    target: Mapping[str, Any], *, kind: TargetKind, file_ids: set[str]
) -> dict[str, Any]:
    raw = deepcopy(dict(target))
    region_key = "src_region_hash" if kind == "src" else "dst_region_hash"
    allowed_keys = {"file_id", "path", "lines", region_key, "region_hash"}
    for key in raw:
        if key not in allowed_keys:
            raise ValueError(f"Unknown field '{key}' for target '{kind}'.")

    has_file_id = "file_id" in raw
    has_path = "path" in raw
    if has_file_id == has_path:
        raise ValueError("Targets must include exactly one of 'file_id' or 'path'.")

    result: dict[str, Any] = {}
    if has_file_id:
        file_id_value = raw["file_id"]
        if not isinstance(file_id_value, str) or not file_id_value:
            raise ValueError("Target 'file_id' must be a non-empty string.")
        if file_id_value not in file_ids:
            raise ValueError(
                f"Target for {kind} references unknown file id '{file_id_value}'."
            )
        result["file_id"] = file_id_value
    else:
        path_value = raw["path"]
        if not isinstance(path_value, str) or not path_value:
            raise ValueError("Target 'path' must be a non-empty string.")
        result["path"] = path_value

    if "lines" in raw:
        result["lines"] = _normalize_line_span(raw["lines"])

    if "region_hash" in raw:
        if region_key in raw:
            raise ValueError(
                "Targets cannot define both 'region_hash' and the schema-specific key."
            )
        raw[region_key] = raw.pop("region_hash")

    if region_key in raw:
        result[region_key] = _normalize_hash(raw[region_key])

    return result


def _normalize_line_span(lines: LineSpan | Mapping[str, Any]) -> dict[str, int]:
    if isinstance(lines, LineSpan):
        data: dict[str, int] = {"start": lines.start}
        if lines.end is not None:
            data["end"] = lines.end
        return data
    if not isinstance(lines, Mapping):
        raise ValueError("Line span must be provided as a mapping or LineSpan.")
    raw = dict(lines)
    start_value = raw.get("start")
    if not isinstance(start_value, int):
        raise ValueError("Line spans must include an integer 'start'.")
    if start_value < 1:
        raise ValueError("Line span 'start' must be >= 1.")
    result: dict[str, int] = {"start": start_value}
    if "end" in raw:
        end_value = raw["end"]
        if not isinstance(end_value, int):
            raise ValueError("Line span 'end' must be an integer when provided.")
        if end_value < start_value:
            raise ValueError("Line span 'end' must be >= 'start'.")
        result["end"] = end_value
    return result


def _normalize_hash(
    value: HashDigest | RegionHash | Mapping[str, Any],
) -> dict[str, str]:
    if isinstance(value, (HashDigest, RegionHash)):
        return {"algo": value.algo, "value": value.value}
    if not isinstance(value, Mapping):
        raise ValueError("Hash digests must be mappings or HashDigest instances.")
    raw = dict(value)
    algo = raw.get("algo")
    if not isinstance(algo, str) or not algo:
        raise ValueError("Hash digests require a non-empty 'algo' string.")
    digest_value = raw.get("value")
    if not isinstance(digest_value, str) or not digest_value:
        raise ValueError("Hash digests require a non-empty 'value' string.")
    return {"algo": algo, "value": digest_value}
