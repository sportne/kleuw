"""Utilities for working with the Kleuw JSON schema."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from copy import deepcopy
from json import JSONDecodeError
from pathlib import Path
from typing import Any

__all__ = ["load_schema", "validate_project"]

_SCHEMA_CACHE: dict[str, Any] | None = None
_ALLOWED_LINK_TYPES: frozenset[str] | None = None
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "spec" / "kleuw.schema.json"

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_WHITESPACE_RE = re.compile(r"\s")


def load_schema() -> dict[str, Any]:
    """Load the Kleuw JSON schema from disk.

    Returns:
        A deep copy of the loaded JSON schema.

    Raises:
        RuntimeError: If the schema cannot be read or parsed.
    """

    return deepcopy(_get_schema())


def validate_project(data: dict[str, Any]) -> list[str]:
    """Validate a project dictionary against the Kleuw schema rules.

    Args:
        data: The JSON-like mapping representing a Kleuw project.

    Returns:
        A list of validation error messages. The list is empty when the project
        data satisfies the schema requirements.

    Raises:
        RuntimeError: If the schema definition cannot be loaded.
    """

    _ensure_link_types()

    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Project root must be a JSON object."]

    allowed_top_level = {"version", "files", "links", "metadata"}
    for key in data:
        if key not in allowed_top_level:
            errors.append(f"Unknown top-level field '{key}'.")

    for required in ("version", "files", "links"):
        if required not in data:
            errors.append(f"Missing required field '{required}'.")

    if "version" in data:
        version = data["version"]
        if not isinstance(version, int):
            errors.append("Field 'version' must be an integer equal to 1.")
        elif version != 1:
            errors.append("Field 'version' must equal 1.")

    file_ids: set[str] = set()
    if "files" in data:
        files_value = data["files"]
        if not isinstance(files_value, list):
            errors.append("Field 'files' must be an array of file objects.")
        else:
            file_errors, file_ids = _validate_files(files_value)
            errors.extend(file_errors)

    if "links" in data:
        links_value = data["links"]
        if not isinstance(links_value, list):
            errors.append("Field 'links' must be an array of link objects.")
        else:
            link_errors = _validate_links(links_value, file_ids)
            errors.extend(link_errors)

    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("Field 'metadata' must be an object when provided.")

    return errors


def _get_schema() -> dict[str, Any]:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        try:
            with _SCHEMA_PATH.open("r", encoding="utf-8") as handle:
                _SCHEMA_CACHE = json.load(handle)
        except (OSError, JSONDecodeError) as exc:  # pragma: no cover - fatal
            raise RuntimeError(f"Unable to load Kleuw schema: {exc}") from exc
    return _SCHEMA_CACHE


def _ensure_link_types() -> None:
    global _ALLOWED_LINK_TYPES
    if _ALLOWED_LINK_TYPES is None:
        schema = _get_schema()
        try:
            enum_values = schema["$defs"]["LinkEntry"]["properties"]["type"]["enum"]
        except KeyError as exc:  # pragma: no cover - schema corruption
            raise RuntimeError(
                "Kleuw schema is missing link type definitions."
            ) from exc
        _ALLOWED_LINK_TYPES = frozenset(str(value) for value in enum_values)


def _validate_files(files: Iterable[Any]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(files):
        location = f"files[{index}]"
        errors.extend(_validate_file_entry(entry, location, seen_ids))
    return errors, seen_ids


def _validate_file_entry(entry: Any, location: str, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        errors.append(f"{location} must be an object.")
        return errors

    allowed_keys = {"id", "path", "hash", "lang", "note", "aliases"}
    errors.extend(_validate_allowed_keys(entry, allowed_keys, location))

    if "id" not in entry:
        errors.append(f"{location} missing required field 'id'.")
    else:
        file_id = entry["id"]
        if not isinstance(file_id, str):
            errors.append(f"{location}.id must be a string.")
        elif file_id == "":
            errors.append(f"{location}.id must be a non-empty string.")
        elif file_id in seen_ids:
            errors.append(f"Duplicate file id '{file_id}' found at {location}.")
        else:
            seen_ids.add(file_id)

    if "path" not in entry:
        errors.append(f"{location} missing required field 'path'.")
    else:
        path_value = entry["path"]
        if not isinstance(path_value, str):
            errors.append(f"{location}.path must be a string.")
        elif path_value == "":
            errors.append(f"{location}.path must be a non-empty string.")

    if "hash" in entry:
        errors.extend(_validate_hash(entry["hash"], f"{location}.hash"))

    if "lang" in entry:
        lang_value = entry["lang"]
        if not isinstance(lang_value, str):
            errors.append(f"{location}.lang must be a string.")
        elif lang_value == "":
            errors.append(f"{location}.lang must be a non-empty string.")

    if "note" in entry and not isinstance(entry["note"], str):
        errors.append(f"{location}.note must be a string.")

    if "aliases" in entry:
        aliases_value = entry["aliases"]
        if not isinstance(aliases_value, list):
            errors.append(f"{location}.aliases must be a list of non-empty strings.")
        else:
            for alias_index, alias in enumerate(aliases_value):
                if not isinstance(alias, str):
                    errors.append(
                        f"{location}.aliases[{alias_index}] must be a non-empty string."
                    )
                elif alias == "":
                    errors.append(
                        f"{location}.aliases[{alias_index}] must be a non-empty string."
                    )

    return errors


def _validate_links(links: Iterable[Any], file_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(links):
        location = f"links[{index}]"
        errors.extend(_validate_link_entry(entry, location, seen_ids, file_ids))
    return errors


def _validate_link_entry(
    entry: Any, location: str, seen_ids: set[str], file_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        errors.append(f"{location} must be an object.")
        return errors

    allowed_keys = {
        "id",
        "type",
        "src",
        "dst",
        "directed",
        "created",
        "author",
        "tags",
        "note",
    }
    errors.extend(_validate_allowed_keys(entry, allowed_keys, location))

    for required in ("id", "type", "src", "dst"):
        if required not in entry:
            errors.append(f"{location} missing required field '{required}'.")

    if "id" in entry:
        link_id = entry["id"]
        if not isinstance(link_id, str):
            errors.append(f"{location}.id must be a string.")
        elif link_id == "":
            errors.append(f"{location}.id must be a non-empty string.")
        elif link_id in seen_ids:
            errors.append(f"Duplicate link id '{link_id}' found at {location}.")
        else:
            seen_ids.add(link_id)

    if "type" in entry:
        link_type = entry["type"]
        if not isinstance(link_type, str):
            errors.append(f"{location}.type must be a string.")
        else:
            allowed_types = _ALLOWED_LINK_TYPES or frozenset()
            if link_type not in allowed_types:
                allowed = ", ".join(sorted(allowed_types))
                errors.append(f"{location}.type must be one of: {allowed}.")

    if "src" in entry:
        errors.extend(
            _validate_target(
                entry["src"], f"{location}.src", kind="src", file_ids=file_ids
            )
        )
    if "dst" in entry:
        errors.extend(
            _validate_target(
                entry["dst"], f"{location}.dst", kind="dst", file_ids=file_ids
            )
        )

    if "directed" in entry and not isinstance(entry["directed"], bool):
        errors.append(f"{location}.directed must be a boolean.")

    if "created" in entry and not isinstance(entry["created"], str):
        errors.append(f"{location}.created must be a string.")

    if "author" in entry and not isinstance(entry["author"], str):
        errors.append(f"{location}.author must be a string.")

    if "tags" in entry:
        tags_value = entry["tags"]
        if not isinstance(tags_value, list):
            errors.append(
                f"{location}.tags must be a list of non-empty strings without whitespace."
            )
        else:
            for tag_index, tag in enumerate(tags_value):
                if not isinstance(tag, str) or tag == "" or _WHITESPACE_RE.search(tag):
                    errors.append(
                        f"{location}.tags[{tag_index}] must be a non-empty string without whitespace."
                    )

    if "note" in entry and not isinstance(entry["note"], str):
        errors.append(f"{location}.note must be a string.")

    return errors


def _validate_target(
    target: Any, location: str, *, kind: str, file_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    if not isinstance(target, dict):
        errors.append(f"{location} must be an object.")
        return errors

    hash_key = "src_region_hash" if kind == "src" else "dst_region_hash"
    allowed_keys = {"file_id", "path", "lines", hash_key}
    errors.extend(_validate_allowed_keys(target, allowed_keys, location))

    has_file_id = "file_id" in target
    has_path = "path" in target
    if has_file_id == has_path:
        errors.append(f"{location} must include exactly one of 'file_id' or 'path'.")

    if has_file_id:
        file_id_value = target["file_id"]
        if not isinstance(file_id_value, str):
            errors.append(f"{location}.file_id must be a string.")
        elif file_id_value == "":
            errors.append(f"{location}.file_id must be a non-empty string.")
        elif file_id_value not in file_ids:
            errors.append(
                f"{location}.file_id references unknown file id '{file_id_value}'."
            )

    if has_path:
        path_value = target["path"]
        if not isinstance(path_value, str):
            errors.append(f"{location}.path must be a string.")
        elif path_value == "":
            errors.append(f"{location}.path must be a non-empty string.")

    if "lines" in target:
        errors.extend(_validate_line_span(target["lines"], f"{location}.lines"))

    if hash_key in target:
        errors.extend(_validate_hash(target[hash_key], f"{location}.{hash_key}"))

    return errors


def _validate_hash(value: Any, location: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{location} must be an object."]

    errors = _validate_allowed_keys(value, {"algo", "value"}, location)

    if "algo" not in value:
        errors.append(f"{location} missing required field 'algo'.")
    else:
        algo = value["algo"]
        if not isinstance(algo, str):
            errors.append(f"{location}.algo must be a string.")
        elif algo == "":
            errors.append(f"{location}.algo must be a non-empty string.")

    if "value" not in value:
        errors.append(f"{location} missing required field 'value'.")
    else:
        hash_value = value["value"]
        if not isinstance(hash_value, str):
            errors.append(f"{location}.value must be a string.")
        elif hash_value == "":
            errors.append(f"{location}.value must be a non-empty string.")
        else:
            if len(hash_value) < 16:
                errors.append(f"{location}.value must be at least 16 hex characters.")
            if not _HEX_RE.fullmatch(hash_value):
                errors.append(
                    f"{location}.value must contain only hexadecimal characters."
                )

    return errors


def _validate_line_span(value: Any, location: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{location} must be an object."]

    errors = _validate_allowed_keys(value, {"start", "end"}, location)

    if "start" not in value:
        errors.append(f"{location} missing required field 'start'.")
        start_value: int | None = None
    else:
        start = value["start"]
        if not isinstance(start, int):
            errors.append(f"{location}.start must be an integer.")
            start_value = None
        else:
            start_value = start
            if start < 1:
                errors.append(f"{location}.start must be >= 1.")
    if "end" in value:
        end = value["end"]
        if not isinstance(end, int):
            errors.append(f"{location}.end must be an integer.")
        else:
            if end < 1:
                errors.append(f"{location}.end must be >= 1.")
            if "start" in value and isinstance(start_value, int) and end < start_value:
                errors.append(f"{location}.end must be >= start.")

    return errors


def _validate_allowed_keys(
    value: dict[str, Any], allowed: set[str], location: str
) -> list[str]:
    errors: list[str] = []
    for key in value:
        if key not in allowed:
            errors.append(f"{location} contains unknown field '{key}'.")
    return errors
