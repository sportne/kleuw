"""Command-line interface scaffolding for Kleuw.

The CLI will eventually satisfy the workflow requirements described in
``spec/kleuw_cli.md`` and ``spec/kleuw_requirements.md``.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from . import schema
from .hashing import compute_file_hash, compute_region_hash
from .io import ProjectIOError, load_project, save_project
from .model import FileEntry, HashDigest, LineSpan, Link, LinkType, RegionHash, Target
from .project import Project
from .staleness import LinkStalenessResult, check_link_staleness

__all__ = ["build_parser", "main", "DEFAULT_PARSER"]

_LINE_RANGE_PATTERN = re.compile(r":(\d+(?:-\d+)?)$")

CommandHandler = Callable[[Namespace], int]
if TYPE_CHECKING:
    SubparserCollection = _SubParsersAction[ArgumentParser]
else:  # pragma: no cover - runtime fallback for typing helper
    SubparserCollection = _SubParsersAction


def build_parser() -> ArgumentParser:
    """Build the root argument parser with all CLI subcommands."""

    parser = ArgumentParser(
        prog="kleuw", description="Traceability project management CLI"
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    _add_init_parser(subparsers)
    _add_add_file_parser(subparsers)
    _add_list_files_parser(subparsers)
    _add_create_link_parser(subparsers)
    _add_list_links_parser(subparsers)
    _add_check_parser(subparsers)
    _add_recompute_parser(subparsers)
    _add_validate_parser(subparsers)
    _add_export_parser(subparsers)

    return parser


def _add_init_parser(subparsers: SubparserCollection) -> None:
    """Register the ``init`` subcommand."""

    parser = subparsers.add_parser(
        "init",
        help="Create a new Kleuw project file",
        description="Create a new Kleuw project JSON file with the default structure.",
    )
    parser.add_argument("project", help="Path to the project JSON file to initialize")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the project file if it already exists",
    )
    parser.set_defaults(handler=_handle_init)


def _add_add_file_parser(subparsers: SubparserCollection) -> None:
    """Register the ``add-file`` subcommand."""

    parser = subparsers.add_parser(
        "add-file",
        help="Add a file entry to the project",
        description="Add or register a file path within an existing Kleuw project.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument("path", help="Path to the file to track")
    parser.add_argument(
        "--id", dest="file_id", help="Optional explicit file identifier"
    )
    parser.add_argument(
        "--hash",
        action="store_true",
        help="Compute and store a file-level hash when adding the file",
    )
    parser.set_defaults(handler=_handle_add_file)


def _add_list_files_parser(subparsers: SubparserCollection) -> None:
    """Register the ``list-files`` subcommand."""

    parser = subparsers.add_parser(
        "list-files",
        help="List files recorded in the project",
        description="Display tracked files in tabular or JSON form.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of a table",
    )
    parser.set_defaults(handler=_handle_list_files)


def _add_create_link_parser(subparsers: SubparserCollection) -> None:
    """Register the ``create-link`` subcommand."""

    parser = subparsers.add_parser(
        "create-link",
        help="Create a new traceability link",
        description="Create a new link between two file regions.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--src", required=True, help="Source path with optional line range"
    )
    parser.add_argument(
        "--dst", required=True, help="Destination path with optional line range"
    )
    parser.add_argument("--type", required=True, help="Relationship type identifier")
    parser.add_argument("--note", help="Optional note describing the link")
    parser.add_argument(
        "--tags",
        help="Comma-separated list of tags associated with the link",
    )
    parser.set_defaults(handler=_handle_create_link)


def _add_list_links_parser(subparsers: SubparserCollection) -> None:
    """Register the ``list-links`` subcommand."""

    parser = subparsers.add_parser(
        "list-links",
        help="List links recorded in the project",
        description="Display links with optional filtering and JSON output.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of a table",
    )
    parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Only show links that are currently stale",
    )
    parser.add_argument("--type", dest="link_type", help="Filter by relationship type")
    parser.set_defaults(handler=_handle_list_links)


def _add_check_parser(subparsers: SubparserCollection) -> None:
    """Register the ``check`` subcommand."""

    parser = subparsers.add_parser(
        "check",
        help="Check for stale links",
        description="Recompute region hashes and report stale links.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--link-id",
        dest="link_ids",
        nargs="+",
        help="Restrict the check to one or more link identifiers",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of a table",
    )
    parser.set_defaults(handler=_handle_check)


def _add_recompute_parser(subparsers: SubparserCollection) -> None:
    """Register the ``recompute`` subcommand."""

    parser = subparsers.add_parser(
        "recompute",
        help="Recompute stored hashes",
        description="Update stored region hashes to the current file content.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--link-id",
        dest="link_ids",
        nargs="+",
        help="Restrict the recomputation to one or more link identifiers",
    )
    parser.set_defaults(handler=_handle_recompute)


def _add_validate_parser(subparsers: SubparserCollection) -> None:
    """Register the ``validate`` subcommand."""

    parser = subparsers.add_parser(
        "validate",
        help="Validate a project file",
        description="Validate the Kleuw project structure against the schema.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.set_defaults(handler=_handle_validate)


def _add_export_parser(subparsers: SubparserCollection) -> None:
    """Register the ``export`` subcommand."""

    parser = subparsers.add_parser(
        "export",
        help="Export project data",
        description="Export project information in a selected format.",
    )
    parser.add_argument("project", help="Path to the project JSON file")
    parser.add_argument(
        "--format",
        choices=("json", "csv", "txt"),
        required=True,
        help="Output format",
    )
    parser.add_argument(
        "--stale",
        action="store_true",
        help="Only include stale links in the export",
    )
    parser.set_defaults(handler=_handle_export)


def _print_error(message: str) -> None:
    """Emit ``message`` to standard error with a consistent prefix."""

    print(f"Error: {message}", file=sys.stderr)


def _print_json(payload: Any) -> None:
    """Pretty-print ``payload`` to standard output as JSON."""

    print(json.dumps(payload, indent=2, sort_keys=True))


def _format_optional(value: object | None) -> str:
    """Return a placeholder when ``value`` is ``None`` or empty."""

    if value is None:
        return "-"
    text = str(value)
    return text if text.strip() else "-"


def _format_hash(hash_value: object | None) -> str:
    """Format ``hash_value`` into ``algo:value`` or ``-`` when missing."""

    digest = _normalize_hash_object(hash_value)
    if digest is None:
        return "-"
    algo, value = digest
    return f"{algo}:{value}"


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Render ``rows`` under ``headers`` in a simple fixed-width table."""

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    header_line = "  ".join(
        header.ljust(width) for header, width in zip(headers, widths, strict=False)
    )
    print(header_line)
    for row in rows:
        line = "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=False)
        )
        print(line)


def _format_target(target: object | None) -> str:
    """Render a ``target`` mapping into ``location[:lines]`` form."""

    if not isinstance(target, Mapping):
        return "-"
    location = str(target.get("file_id") or target.get("path") or "-")
    lines = target.get("lines")
    if isinstance(lines, Mapping):
        start = lines.get("start")
        end = lines.get("end")
        if isinstance(start, int):
            line_suffix = f":{start}"
            if isinstance(end, int):
                line_suffix = f":{start}-{end}"
            location = f"{location}{line_suffix}"
    return location


def _evaluate_link_staleness(
    entry: Mapping[str, Any], *, file_lookup: Mapping[str, Mapping[str, Any]]
) -> bool:
    """Return ``True`` when ``entry`` represents a stale link."""

    try:
        link = _link_from_mapping(entry)
    except ValueError:
        return False
    result = check_link_staleness(link, file_lookup=file_lookup)
    return result.stale


def _link_from_mapping(entry: Mapping[str, Any]) -> Link:
    """Convert a serialized link mapping into a :class:`Link`."""

    src_data = entry.get("src")
    dst_data = entry.get("dst")
    if not isinstance(src_data, Mapping) or not isinstance(dst_data, Mapping):
        raise ValueError("Links must define 'src' and 'dst' targets.")
    link_type = entry.get("type")
    if link_type is None:
        raise ValueError("Links must define a 'type'.")
    tags = entry.get("tags") or ()
    if isinstance(tags, str):
        tags_value: Sequence[str] = (tags,)
    else:
        try:
            tags_value = tuple(str(tag) for tag in tags)
        except TypeError as exc:
            raise ValueError("Link tags must be iterable.") from exc

    directed = entry.get("directed")
    directed_value = True if directed is None else bool(directed)
    return Link(
        id=str(entry.get("id", "")),
        type=LinkType(link_type),
        src=_target_from_mapping(src_data, region_key="src_region_hash"),
        dst=_target_from_mapping(dst_data, region_key="dst_region_hash"),
        directed=directed_value,
        created=entry.get("created"),
        author=entry.get("author"),
        tags=tags_value,
        note=entry.get("note"),
    )


def _target_from_mapping(target: Mapping[str, Any], *, region_key: str) -> Target:
    """Convert serialized target mapping to :class:`Target`."""

    file_id = target.get("file_id")
    path = target.get("path")
    lines = _line_span_from_mapping(target.get("lines"))
    hash_data = target.get(region_key) or target.get("region_hash")
    region_hash = _region_hash_from_mapping(hash_data) if hash_data else None
    return Target(file_id=file_id, path=path, lines=lines, region_hash=region_hash)


def _line_span_from_mapping(data: object | None) -> LineSpan | None:
    """Convert a serialized line span to :class:`LineSpan`."""

    if data is None:
        return None
    if isinstance(data, LineSpan):
        return data
    if not isinstance(data, Mapping):
        raise ValueError("Line span must be a mapping.")
    start = data.get("start")
    end = data.get("end")
    if not isinstance(start, int):
        raise ValueError("Line span requires an integer 'start'.")
    if end is not None and not isinstance(end, int):
        raise ValueError("Line span 'end' must be an integer when provided.")
    return LineSpan(start=start, end=end)


def _region_hash_from_mapping(data: object) -> RegionHash:
    """Convert ``data`` into a :class:`RegionHash`."""

    if isinstance(data, RegionHash):
        return data
    if isinstance(data, HashDigest):
        return RegionHash(algo=data.algo, value=data.value)
    if isinstance(data, Mapping):
        algo = data.get("algo")
        value = data.get("value")
        if isinstance(algo, str) and isinstance(value, str):
            return RegionHash(algo=algo, value=value)
    raise ValueError("Region hash must define 'algo' and 'value'.")


def _normalize_hash_object(value: object | None) -> tuple[str, str] | None:
    """Return a ``(algo, value)`` tuple for hash-like ``value``."""

    if isinstance(value, (HashDigest, RegionHash)):
        return value.algo, value.value
    if isinstance(value, Mapping):
        algo = value.get("algo")
        digest_value = value.get("value")
        if isinstance(algo, str) and isinstance(digest_value, str):
            return algo, digest_value
    return None


def _build_file_lookup(project: Project) -> dict[str, Mapping[str, Any]]:
    """Return a mapping of file identifiers to their serialized entries."""

    lookup: dict[str, Mapping[str, Any]] = {}
    for entry in project.files:
        if not isinstance(entry, Mapping):
            continue
        file_id = entry.get("id")
        if isinstance(file_id, str) and file_id:
            lookup[file_id] = entry
    return lookup


def _select_link_entries(
    project: Project, link_ids: Sequence[str] | None
) -> list[dict[str, Any]]:
    """Return the subset of link entries referenced by ``link_ids``."""

    if link_ids:
        selected: list[dict[str, Any]] = []
        missing: list[str] = []
        for link_id in link_ids:
            entry = project.find_link_by_id(link_id)
            if not isinstance(entry, dict):
                missing.append(str(link_id))
                continue
            selected.append(entry)
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"Unknown link id(s): {missing_list}.")
        return selected

    entries: list[dict[str, Any]] = []
    for entry in project.links:
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _format_reasons(reasons: Sequence[str]) -> str:
    """Return a friendly representation of staleness ``reasons``."""

    if not reasons:
        return "-"
    return "; ".join(reasons)


def _annotate_links_with_staleness(
    project: Project,
) -> list[tuple[dict[str, Any], LinkStalenessResult]]:
    """Return ``project`` links paired with their staleness results."""

    file_lookup = _build_file_lookup(project)
    annotated: list[tuple[dict[str, Any], LinkStalenessResult]] = []
    for entry in project.links:
        if not isinstance(entry, dict):
            continue
        entry_dict = entry
        try:
            link = _link_from_mapping(entry_dict)
        except ValueError as exc:
            identifier = entry_dict.get("id")
            label = f"link '{identifier}'" if identifier else "link"
            raise ValueError(f"Invalid {label}: {exc}") from exc
        result = check_link_staleness(link, file_lookup=file_lookup)
        annotated.append((entry_dict, result))
    return annotated


def _link_entry_with_staleness(
    entry: Mapping[str, Any], result: LinkStalenessResult
) -> dict[str, Any]:
    """Return a deep-copied ``entry`` annotated with staleness metadata."""

    payload = deepcopy(dict(entry))
    payload["stale"] = result.stale
    if result.reasons:
        payload["stale_reasons"] = list(result.reasons)
    elif "stale_reasons" in payload:
        del payload["stale_reasons"]
    return payload


def _export_as_json(
    files: Sequence[Mapping[str, Any]],
    links: Sequence[tuple[Mapping[str, Any], LinkStalenessResult]],
    *,
    total_links: int,
    stale_links: int,
    exported_links: int,
) -> None:
    """Emit a JSON payload describing the exported project data."""

    payload = {
        "files": deepcopy(list(files)),
        "links": [_link_entry_with_staleness(entry, result) for entry, result in links],
        "summary": {
            "files": len(files),
            "links": total_links,
            "stale_links": stale_links,
            "exported_links": exported_links,
        },
    }
    _print_json(payload)


def _export_as_csv(
    files: Sequence[Mapping[str, Any]],
    links: Sequence[tuple[Mapping[str, Any], LinkStalenessResult]],
) -> None:
    """Emit CSV rows covering files and link staleness details."""

    writer = csv.writer(sys.stdout)
    writer.writerow(
        [
            "section",
            "id",
            "path",
            "lang",
            "note",
            "hash",
            "type",
            "src",
            "dst",
            "stale",
            "reasons",
        ]
    )
    for entry in files:
        writer.writerow(
            [
                "file",
                str(entry.get("id", "")),
                str(entry.get("path", "")),
                _format_optional(entry.get("lang")),
                _format_optional(entry.get("note")),
                _format_hash(entry.get("hash")),
                "",
                "",
                "",
                "",
                "",
            ]
        )
    for entry, result in links:
        writer.writerow(
            [
                "link",
                str(entry.get("id", "")),
                "",
                "",
                "",
                "",
                str(entry.get("type", "")),
                _format_target(entry.get("src")),
                _format_target(entry.get("dst")),
                "yes" if result.stale else "no",
                _format_reasons(result.reasons),
            ]
        )


def _export_as_text(
    files: Sequence[Mapping[str, Any]],
    links: Sequence[tuple[Mapping[str, Any], LinkStalenessResult]],
    *,
    total_links: int,
    stale_links: int,
    stale_only: bool,
) -> None:
    """Emit human-readable tables describing files and links."""

    file_rows: list[list[str]] = []
    for entry in files:
        file_rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("path", "")),
                _format_optional(entry.get("lang")),
                _format_hash(entry.get("hash")),
                _format_optional(entry.get("note")),
            ]
        )

    print("Files:")
    _print_table(["ID", "PATH", "LANG", "HASH", "NOTE"], file_rows)
    if not file_rows:
        print("(no files)")
    print()

    link_rows: list[list[str]] = []
    for entry, result in links:
        link_rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("type", "")),
                _format_target(entry.get("src")),
                _format_target(entry.get("dst")),
                "STALE" if result.stale else "OK",
                _format_reasons(result.reasons),
            ]
        )

    print("Links:")
    _print_table(["ID", "TYPE", "SRC", "DST", "STATUS", "DETAILS"], link_rows)
    if not link_rows:
        print("(no links)")
    print()

    print(f"Total links: {total_links}")
    print(f"Stale links: {stale_links}")
    print(f"Exported links: {len(links)}" + (" (stale only)" if stale_only else ""))


def _resolve_target_path_entry(
    target: Mapping[str, Any],
    *,
    file_lookup: Mapping[str, Mapping[str, Any]],
    label: str,
) -> Path:
    """Resolve the filesystem path for ``target``."""

    path_value = target.get("path")
    if isinstance(path_value, str) and path_value:
        return Path(path_value)

    file_id = target.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise ValueError(
            f"{label.capitalize()} target must define 'file_id' or 'path'."
        )

    file_entry = file_lookup.get(file_id)
    if not isinstance(file_entry, Mapping):
        raise ValueError(
            f"{label.capitalize()} target references unknown file id '{file_id}'."
        )

    entry_path = file_entry.get("path")
    if not isinstance(entry_path, str) or not entry_path:
        raise ValueError(f"File '{file_id}' does not define a usable path.")
    return Path(entry_path)


def _compute_entry_region_hash(
    target: Mapping[str, Any],
    *,
    region_key: str,
    file_lookup: Mapping[str, Mapping[str, Any]],
    label: str,
) -> RegionHash:
    """Compute the region hash for a serialized target entry."""

    try:
        lines = _line_span_from_mapping(target.get("lines"))
    except ValueError as exc:
        raise ValueError(f"Invalid line range for {label}: {exc}") from exc

    path = _resolve_target_path_entry(target, file_lookup=file_lookup, label=label)
    digest = _normalize_hash_object(target.get(region_key))
    if digest is None:
        digest = _normalize_hash_object(target.get("region_hash"))
    algo = digest[0] if digest is not None else None
    start_line = lines.start if lines else None
    end_line = lines.end if lines else None
    try:
        if algo:
            return compute_region_hash(
                path, start_line=start_line, end_line=end_line, algo=algo
            )
        return compute_region_hash(path, start_line=start_line, end_line=end_line)
    except FileNotFoundError as exc:
        raise ValueError(f"{label.capitalize()} file '{path}' does not exist.") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{label.capitalize()} file '{path}' is not valid UTF-8."
        ) from exc
    except ValueError as exc:
        raise ValueError(f"Invalid line range for {label}: {exc}") from exc


def _update_target_region_hash(
    target: dict[str, Any], *, region_key: str, region_hash: RegionHash
) -> None:
    """Persist ``region_hash`` back onto the serialized target mapping."""

    target[region_key] = {"algo": region_hash.algo, "value": region_hash.value}


def _generate_file_id(project: Project) -> str:
    """Return the next available ``file-<n>`` identifier for ``project``."""

    counter = 1
    while True:
        candidate = f"file-{counter}"
        if not project.find_file_by_id(candidate):
            return candidate
        counter += 1


def _generate_link_id(project: Project) -> str:
    """Return the next available ``link-<n>`` identifier for ``project``."""

    counter = 1
    while True:
        candidate = f"link-{counter}"
        if not project.find_link_by_id(candidate):
            return candidate
        counter += 1


def _parse_target_argument(value: str, *, label: str) -> tuple[str, LineSpan | None]:
    """Split ``value`` into ``(path, LineSpan | None)`` using CLI syntax."""

    text = value.strip()
    if not text:
        raise ValueError(f"{label.capitalize()} target cannot be empty.")

    match = _LINE_RANGE_PATTERN.search(text)
    if match:
        line_spec = match.group(1)
        path_text = text[: match.start()]
        if not path_text:
            raise ValueError(f"{label.capitalize()} path cannot be empty.")
        lines = _parse_line_spec(line_spec, label=label)
    else:
        path_text = text
        lines = None

    return path_text, lines


def _parse_line_spec(spec: str, *, label: str) -> LineSpan:
    """Parse ``spec`` into a :class:`LineSpan`."""

    if "-" in spec:
        start_text, end_text = spec.split("-", 1)
        if not end_text:
            raise ValueError(f"Invalid line range for {label}: missing end line.")
    else:
        start_text = spec
        end_text = None

    try:
        start = int(start_text)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Invalid line range for {label}: '{start_text}' is not a number."
        ) from exc
    if start < 1:
        raise ValueError(f"Invalid line range for {label}: start must be >= 1.")

    end = None
    if end_text is not None:
        try:
            end = int(end_text)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(
                f"Invalid line range for {label}: '{end_text}' is not a number."
            ) from exc
        if end < start:
            raise ValueError(f"Invalid line range for {label}: end must be >= start.")

    try:
        return LineSpan(start=start, end=end)
    except ValueError as exc:  # pragma: no cover - dataclass validation
        raise ValueError(f"Invalid line range for {label}: {exc}") from exc


def _parse_tags(value: str | None) -> tuple[str, ...]:
    """Return normalized tags parsed from ``value``."""

    if value is None:
        return ()
    tags = [tag.strip() for tag in value.split(",")]
    if not all(tags) or not tags:
        raise ValueError("Tags must be non-empty strings.")
    return tuple(tags)


def _build_target(
    project: Project,
    *,
    path_text: str,
    lines: LineSpan | None,
    label: str,
) -> Target:
    """Create a :class:`Target` for ``path_text`` and ``lines``."""

    region_hash = _compute_target_hash(path_text, lines=lines, label=label)
    file_entry = project.find_file_by_path(path_text)
    if file_entry is not None:
        file_id = str(file_entry["id"])
        return Target(file_id=file_id, lines=lines, region_hash=region_hash)
    return Target(path=path_text, lines=lines, region_hash=region_hash)


def _compute_target_hash(
    path_text: str, *, lines: LineSpan | None, label: str
) -> RegionHash:
    """Compute a region hash for ``path_text`` and ``lines``."""

    start_line = lines.start if lines is not None else None
    end_line = lines.end if lines is not None else None
    try:
        return compute_region_hash(path_text, start_line=start_line, end_line=end_line)
    except FileNotFoundError as exc:
        raise ValueError(
            f"{label.capitalize()} file '{path_text}' does not exist."
        ) from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{label.capitalize()} file '{path_text}' is not valid UTF-8."
        ) from exc
    except ValueError as exc:
        raise ValueError(f"Invalid line range for {label}: {exc}") from exc


def _handle_init(args: Namespace) -> int:
    """Create a new Kleuw project JSON file."""

    project_path = Path(args.project)
    if project_path.exists() and not args.force:
        _print_error(
            f"Project file '{project_path}' already exists. Use --force to overwrite."
        )
        return 1

    try:
        project_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _print_error(f"Unable to create directory '{project_path.parent}': {exc}")
        return 1

    project = Project(version=1)
    try:
        save_project(project_path, project)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1
    return 0


def _handle_add_file(args: Namespace) -> int:
    """Add a file entry to an existing Kleuw project."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    file_path = Path(args.path)
    if not file_path.is_file():
        _print_error(f"File '{file_path}' does not exist or is not a file.")
        return 1

    file_id = args.file_id.strip() if args.file_id else None
    if file_id is not None and not file_id:
        _print_error("File id cannot be empty.")
        return 1
    if file_id is None:
        file_id = _generate_file_id(project)

    file_hash = None
    if args.hash:
        try:
            file_hash = compute_file_hash(file_path)
        except OSError as exc:
            _print_error(f"Unable to hash file '{file_path}': {exc}")
            return 1

    entry = FileEntry(id=file_id, path=str(file_path), hash=file_hash)
    try:
        project.add_file(entry)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        save_project(project_path, project)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    return 0


def _handle_list_files(args: Namespace) -> int:
    """Display tracked files from the selected project."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    if args.json:
        _print_json({"files": project.files})
        return 0

    rows: list[list[str]] = []
    for entry in project.files:
        if not isinstance(entry, Mapping):
            continue
        rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("path", "")),
                _format_optional(entry.get("lang")),
                _format_hash(entry.get("hash")),
                _format_optional(entry.get("note")),
            ]
        )

    _print_table(["ID", "PATH", "LANG", "HASH", "NOTE"], rows)
    if not rows:
        print("(no files)")
    return 0


def _handle_create_link(args: Namespace) -> int:
    """Create a new traceability link between two targets."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    try:
        link_type = LinkType(args.type)
    except ValueError:
        _print_error(f"Unknown link type '{args.type}'.")
        return 1

    try:
        src_path, src_lines = _parse_target_argument(args.src, label="source")
        dst_path, dst_lines = _parse_target_argument(args.dst, label="destination")
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        tags = _parse_tags(args.tags)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        src_target = _build_target(
            project, path_text=src_path, lines=src_lines, label="source"
        )
        dst_target = _build_target(
            project, path_text=dst_path, lines=dst_lines, label="destination"
        )
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    link_id = _generate_link_id(project)
    link = Link(
        id=link_id,
        type=link_type,
        src=src_target,
        dst=dst_target,
        tags=tags,
        note=args.note,
    )

    try:
        project.add_link(link)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        save_project(project_path, project)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    print(link_id)
    return 0


def _handle_list_links(args: Namespace) -> int:
    """Display links from the selected project with optional filtering."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    link_entries: list[dict[str, Any]] = []
    for entry in project.links:
        if not isinstance(entry, Mapping):
            continue
        if args.link_type and str(entry.get("type")) != args.link_type:
            continue
        link_entries.append(entry)

    file_lookup = {
        str(entry["id"]): entry
        for entry in project.files
        if isinstance(entry, Mapping) and "id" in entry
    }

    annotated: list[tuple[dict[str, Any], bool]] = []
    for entry in link_entries:
        result = _evaluate_link_staleness(entry, file_lookup=file_lookup)
        if args.stale_only and not result:
            continue
        annotated.append((entry, bool(result)))

    if args.json:
        _print_json({"links": [entry for entry, _ in annotated]})
        return 0

    rows: list[list[str]] = []
    for entry, is_stale in annotated:
        rows.append(
            [
                str(entry.get("id", "")),
                str(entry.get("type", "")),
                _format_target(entry.get("src")),
                _format_target(entry.get("dst")),
                "yes" if is_stale else "no",
                (
                    ",".join(str(tag) for tag in entry.get("tags", []))
                    if entry.get("tags")
                    else "-"
                ),
            ]
        )

    _print_table(["ID", "TYPE", "SRC", "DST", "STALE", "TAGS"], rows)
    if not rows:
        print("(no links)")
    return 0


def _handle_check(args: Namespace) -> int:
    """Run staleness detection for the selected links."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    try:
        link_entries = _select_link_entries(project, args.link_ids)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    file_lookup = _build_file_lookup(project)
    annotated: list[tuple[dict[str, Any], LinkStalenessResult]] = []
    for entry in link_entries:
        try:
            link = _link_from_mapping(entry)
        except ValueError as exc:
            identifier = entry.get("id") if isinstance(entry, Mapping) else None
            label = f"link '{identifier}'" if identifier else "link"
            _print_error(f"Invalid {label}: {exc}")
            return 1
        result = check_link_staleness(link, file_lookup=file_lookup)
        annotated.append((entry, result))

    stale_count = sum(1 for _entry, result in annotated if result.stale)

    if args.json:
        payload = {
            "total": len(annotated),
            "stale": stale_count,
            "results": [
                {
                    "id": result.link_id,
                    "type": str(entry.get("type", "")),
                    "stale": result.stale,
                    **(
                        {"reason": _format_reasons(result.reasons)}
                        if result.reasons
                        else {}
                    ),
                }
                for entry, result in annotated
            ],
        }
        _print_json(payload)
    else:
        rows: list[list[str]] = []
        for entry, result in annotated:
            rows.append(
                [
                    str(entry.get("id", "")),
                    str(entry.get("type", "")),
                    "STALE" if result.stale else "OK",
                    _format_reasons(result.reasons),
                ]
            )
        _print_table(["ID", "TYPE", "STATUS", "DETAILS"], rows)
        if not rows:
            print("(no links)")

    return 1 if stale_count else 0


def _handle_recompute(args: Namespace) -> int:
    """Update stored region hashes for the selected links."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    try:
        link_entries = _select_link_entries(project, args.link_ids)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    if not link_entries:
        return 0

    file_lookup = _build_file_lookup(project)
    for entry in link_entries:
        src_entry = entry.get("src")
        dst_entry = entry.get("dst")
        if not isinstance(src_entry, dict) or not isinstance(dst_entry, dict):
            _print_error("Link entries must define 'src' and 'dst' targets.")
            return 1
        try:
            src_hash = _compute_entry_region_hash(
                src_entry,
                region_key="src_region_hash",
                file_lookup=file_lookup,
                label="source",
            )
            dst_hash = _compute_entry_region_hash(
                dst_entry,
                region_key="dst_region_hash",
                file_lookup=file_lookup,
                label="destination",
            )
        except ValueError as exc:
            identifier = entry.get("id")
            prefix = f"Link '{identifier}' " if identifier else "Link "
            _print_error(prefix + str(exc))
            return 1

        _update_target_region_hash(
            src_entry, region_key="src_region_hash", region_hash=src_hash
        )
        _update_target_region_hash(
            dst_entry, region_key="dst_region_hash", region_hash=dst_hash
        )

    try:
        save_project(project_path, project)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    return 0


def _handle_validate(args: Namespace) -> int:
    """Validate the selected project file against the Kleuw schema."""

    project_path = Path(args.project)
    try:
        with project_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        _print_error(f"Project file '{project_path}' does not exist.")
        return 1
    except json.JSONDecodeError as exc:
        _print_error(
            f"Project file '{project_path}' contains invalid JSON: "
            f"{exc.msg} (line {exc.lineno}, column {exc.colno})."
        )
        return 1
    except OSError as exc:
        _print_error(f"Unable to read project file '{project_path}': {exc}")
        return 1

    errors = schema.validate_project(payload)
    if errors:
        _print_error("Project validation failed.")
        for message in errors:
            print(f"  - {message}", file=sys.stderr)
        return 1

    file_count = len(payload.get("files", [])) if isinstance(payload, Mapping) else 0
    link_count = len(payload.get("links", [])) if isinstance(payload, Mapping) else 0
    print(f"Project is valid ({file_count} files, {link_count} links).")
    return 0


def _handle_export(args: Namespace) -> int:
    """Export project contents and staleness data in the selected format."""

    project_path = Path(args.project)
    try:
        project = load_project(project_path)
    except ProjectIOError as exc:
        _print_error(str(exc))
        return 1

    file_entries: list[dict[str, Any]] = [
        entry for entry in project.files if isinstance(entry, dict)
    ]
    try:
        annotated = _annotate_links_with_staleness(project)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    total_links = len(annotated)
    stale_links = sum(1 for _entry, result in annotated if result.stale)
    selected = [item for item in annotated if not args.stale or item[1].stale]

    if args.format == "json":
        _export_as_json(
            file_entries,
            selected,
            total_links=total_links,
            stale_links=stale_links,
            exported_links=len(selected),
        )
    elif args.format == "csv":
        _export_as_csv(file_entries, selected)
    else:
        _export_as_text(
            file_entries,
            selected,
            total_links=total_links,
            stale_links=stale_links,
            stale_only=bool(args.stale),
        )

    return 0


DEFAULT_PARSER: ArgumentParser = build_parser()


def main(argv: Sequence[str] | None = None) -> int:
    """Program entry point that dispatches to the selected subcommand."""

    parser = build_parser()
    args = parser.parse_args(argv)
    handler: CommandHandler = cast(CommandHandler, vars(args)["handler"])
    return handler(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
