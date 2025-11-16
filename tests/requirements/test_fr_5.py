"""Requirement validation tests for FR-5 (File Catalog)."""

from argparse import Namespace
from pathlib import Path

from kleuw.cli import _handle_add_file
from kleuw.io import load_project
from tests.requirements._cli_helpers import create_project


def test_fr_5_add_file_records_project_path(tmp_path: Path) -> None:
    """FR-5: Users shall be able to add file paths to the project."""

    project_path = tmp_path / "project.json"
    tracked_path = tmp_path / "tracked.txt"
    tracked_path.write_text("hello", encoding="utf-8")
    create_project(project_path)

    exit_code = _handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_path),
            file_id=None,
            hash=False,
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    entry = project.find_file_by_path(str(tracked_path))
    assert entry is not None
    assert entry["path"] == str(tracked_path)
