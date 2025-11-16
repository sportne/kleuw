"""Requirement validation tests for FR-1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kleuw.io import ProjectValidationError, load_project, save_project
from kleuw.model import FileEntry, LineSpan, Link, LinkType, RegionHash, Target
from kleuw.project import Project


INVALID_PROJECT = {
    "version": 1,
    "files": [
        {
            "id": "file-1",
            # missing "path"
        }
    ],
    "links": [],
}


def build_valid_project() -> Project:
    project = Project()
    file_entry = FileEntry(id="file-1", path="README.md", lang="markdown")
    project.add_file(file_entry)

    link = Link(
        id="link-1",
        type=LinkType.REFERS_TO,
        src=Target(
            file_id="file-1",
            lines=LineSpan(start=1, end=3),
            region_hash=RegionHash(algo="sha256", value="a" * 32),
        ),
        dst=Target(
            file_id="file-1",
            lines=LineSpan(start=4, end=6),
            region_hash=RegionHash(algo="sha256", value="b" * 32),
        ),
        note="demonstration",
    )
    project.add_link(link)
    project.metadata = {"name": "demo"}
    return project


def test_fr_1_load_and_save_round_trip(tmp_path: Path) -> None:
    """FR-1: kleuw shall load and save schema-compliant project files."""

    project = build_valid_project()
    source_path = tmp_path / "project.json"
    source_path.write_text(json.dumps(project.to_dict()), encoding="utf-8")

    loaded = load_project(source_path)
    assert loaded.to_dict() == project.to_dict()

    target_path = tmp_path / "copy.json"
    save_project(target_path, loaded)

    saved_payload = json.loads(target_path.read_text(encoding="utf-8"))
    assert saved_payload == project.to_dict()


def test_fr_1_validation_enforced_for_load_and_save(tmp_path: Path) -> None:
    """FR-1: schema validation failures surface for both load/save."""

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(INVALID_PROJECT), encoding="utf-8")

    with pytest.raises(ProjectValidationError):
        load_project(invalid_path)

    project = Project(version=1, files=INVALID_PROJECT["files"], links=[])
    with pytest.raises(ProjectValidationError):
        save_project(tmp_path / "invalid_save.json", project)
