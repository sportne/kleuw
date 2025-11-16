"""Requirement validation tests for FR-6 (File Catalog)."""

from argparse import Namespace
from pathlib import Path

import pytest

from kleuw.cli import _handle_add_file
from kleuw.hashing import compute_file_hash
from kleuw.io import load_project
from tests.requirements._cli_helpers import create_project


def test_fr_6_add_file_requires_existing_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-6: add-file verifies that the referenced path exists."""

    project_path = tmp_path / "project.json"
    missing_path = tmp_path / "missing.txt"
    create_project(project_path)

    exit_code = _handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(missing_path),
            file_id=None,
            hash=False,
        )
    )

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


def test_fr_6_add_file_can_store_hash(tmp_path: Path) -> None:
    """FR-6: add-file can compute and store a sha256 hash when --hash is used."""

    project_path = tmp_path / "project.json"
    tracked_path = tmp_path / "tracked.txt"
    tracked_path.write_text("hash me", encoding="utf-8")
    create_project(project_path)

    exit_code = _handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_path),
            file_id=None,
            hash=True,
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    entry = project.find_file_by_path(str(tracked_path))
    assert entry is not None
    assert entry["hash"]["algo"] == "sha256"
    assert entry["hash"]["value"] == compute_file_hash(tracked_path).value
