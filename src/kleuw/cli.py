"""Command-line interface scaffolding for Kleuw.

The CLI will eventually satisfy the workflow requirements described in
``spec/kleuw_cli.md`` and ``spec/kleuw_requirements.md``.
"""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .hashing import compute_file_hash
from .io import ProjectIOError, load_project, save_project
from .model import FileEntry, HashDigest, LineSpan, Link, LinkType, RegionHash, Target
from .project import Project
from .staleness import check_link_staleness

__all__ = ["build_parser", "main", "DEFAULT_PARSER"]

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


def _unimplemented(name: str) -> int:
    """Raise the standard placeholder exception for unimplemented commands."""

    raise NotImplementedError(f"Command '{name}' is not implemented yet")


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

    if value is None:
        return None
    if isinstance(value, (HashDigest, RegionHash)):
        return value.algo, value.value
    if isinstance(value, Mapping):
        algo = value.get("algo")
        digest_value = value.get("value")
        if isinstance(algo, str) and isinstance(digest_value, str):
            return algo, digest_value
    return None


def _generate_file_id(project: Project) -> str:
    """Return the next available ``file-<n>`` identifier for ``project``."""

    counter = 1
    while True:
        candidate = f"file-{counter}"
        if not project.find_file_by_id(candidate):
            return candidate
        counter += 1


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
    """Placeholder handler for the ``create-link`` subcommand."""

    return _unimplemented("create-link")


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
    """Placeholder handler for the ``check`` subcommand."""

    return _unimplemented("check")


def _handle_recompute(args: Namespace) -> int:
    """Placeholder handler for the ``recompute`` subcommand."""

    return _unimplemented("recompute")


def _handle_validate(args: Namespace) -> int:
    """Placeholder handler for the ``validate`` subcommand."""

    return _unimplemented("validate")


def _handle_export(args: Namespace) -> int:
    """Placeholder handler for the ``export`` subcommand."""

    return _unimplemented("export")


DEFAULT_PARSER: ArgumentParser = build_parser()


def main(argv: Sequence[str] | None = None) -> int:
    """Program entry point that dispatches to the selected subcommand."""

    parser = build_parser()
    args = parser.parse_args(argv)
    handler: CommandHandler = cast(CommandHandler, vars(args)["handler"])
    return handler(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
