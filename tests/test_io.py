"""Tests for Kleuw project IO helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kleuw.io import (
    ProjectIOError,
    ProjectValidationError,
    load_project,
    save_project,
)
from kleuw.project import Project


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_project_success(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    _write_json(project_path, {"version": 1, "files": [], "links": []})

    project = load_project(project_path)

    assert isinstance(project, Project)
    assert project.version == 1
    assert project.files == []
    assert project.links == []


def test_load_project_invalid_json(tmp_path: Path) -> None:
    project_path = tmp_path / "broken.json"
    project_path.write_text("{ invalid", encoding="utf-8")

    with pytest.raises(ProjectIOError):
        load_project(project_path)


def test_load_project_validation_errors(tmp_path: Path) -> None:
    project_path = tmp_path / "missing_fields.json"
    _write_json(project_path, {"version": 1})

    with pytest.raises(ProjectValidationError) as excinfo:
        load_project(project_path)

    assert excinfo.value.errors


def test_save_project_round_trip(tmp_path: Path) -> None:
    project_path = tmp_path / "round.json"
    project = Project(version=1)

    save_project(project_path, project)

    contents = json.loads(project_path.read_text(encoding="utf-8"))
    assert contents == {"version": 1, "files": [], "links": []}


def test_save_project_validation_failure(tmp_path: Path) -> None:
    project_path = tmp_path / "invalid.json"
    project = Project(version=2)

    with pytest.raises(ProjectValidationError):
        save_project(project_path, project)
