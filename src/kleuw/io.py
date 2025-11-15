"""Helpers for reading and writing Kleuw project files."""

from __future__ import annotations

import json
from collections.abc import Iterable
from json import JSONDecodeError
from os import PathLike
from pathlib import Path

from . import schema
from .project import Project

__all__ = [
    "ProjectIOError",
    "ProjectValidationError",
    "load_project",
    "save_project",
]

StrPath = str | PathLike[str]


class ProjectIOError(RuntimeError):
    """Base error raised for project IO failures."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        super().__init__(message)
        self.path: Path | None = path


class ProjectValidationError(ProjectIOError):
    """Raised when project data fails schema validation."""

    def __init__(self, errors: Iterable[str], *, path: Path | None = None) -> None:
        error_list = [str(error) for error in errors]
        message = "Project validation failed: " + "; ".join(error_list)
        super().__init__(message, path=path)
        self.errors: list[str] = error_list


def load_project(path: StrPath) -> Project:
    """Load, validate, and parse a Kleuw project file."""

    project_path = Path(path)
    try:
        with project_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ProjectIOError(
            f"Project file '{project_path}' does not exist.", path=project_path
        ) from exc
    except JSONDecodeError as exc:
        raise ProjectIOError(
            (
                f"Project file '{project_path}' contains invalid JSON: "
                f"{exc.msg} (line {exc.lineno}, column {exc.colno})."
            ),
            path=project_path,
        ) from exc
    except OSError as exc:
        raise ProjectIOError(
            f"Unable to read project file '{project_path}': {exc}",
            path=project_path,
        ) from exc

    errors = schema.validate_project(data)
    if errors:
        raise ProjectValidationError(errors, path=project_path)

    return Project.from_dict(data)


def save_project(path: StrPath, project: Project) -> None:
    """Validate and persist a project to disk in JSON format."""

    project_path = Path(path)
    payload = project.to_dict()
    errors = schema.validate_project(payload)
    if errors:
        raise ProjectValidationError(errors, path=project_path)

    try:
        with project_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        raise ProjectIOError(
            f"Unable to write project file '{project_path}': {exc}",
            path=project_path,
        ) from exc
