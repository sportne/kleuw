"""Requirement FR-25: ``kleuw add-file`` behavior."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.io import load_project
from tests.requirements._cli_helpers import create_project


def test_fr_25_add_file_generates_default_identifier(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    create_project(project_path)
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("tracked", encoding="utf-8")

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path), path=str(tracked_file), file_id=None, hash=False
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    assert project.files == [{"id": "file-1", "path": str(tracked_file)}]


def test_fr_25_add_file_optionally_computes_hash(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    create_project(project_path)
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("hash me", encoding="utf-8")

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_file),
            file_id="explicit",
            hash=True,
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    entry = project.find_file_by_id("explicit")
    assert entry is not None
    assert entry["hash"]["algo"] == "sha256"
    assert len(entry["hash"]["value"]) == 64
