"""Command-line interface scaffolding for Kleuw.

The CLI will eventually satisfy the workflow requirements described in
``spec/kleuw_cli.md`` and ``spec/kleuw_requirements.md``.
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .hashing import compute_file_hash
from .io import ProjectIOError, load_project, save_project
from .model import FileEntry
from .project import Project

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
    """Placeholder handler for the ``list-files`` subcommand."""

    return _unimplemented("list-files")


def _handle_create_link(args: Namespace) -> int:
    """Placeholder handler for the ``create-link`` subcommand."""

    return _unimplemented("create-link")


def _handle_list_links(args: Namespace) -> int:
    """Placeholder handler for the ``list-links`` subcommand."""

    return _unimplemented("list-links")


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
