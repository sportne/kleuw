"""Requirement validation tests for FR-7 (File Catalog)."""

from pathlib import Path

from kleuw.cli import _build_target
from kleuw.model import FileEntry
from kleuw.project import Project


def _project_with_file(file_path: Path) -> Project:
    project = Project()
    project.add_file(FileEntry(id="file-1", path=str(file_path)))
    return project


def test_fr_7_prefers_file_id_for_known_paths(tmp_path: Path) -> None:
    """FR-7: file targets reuse the stable file identifier when available."""

    tracked_path = tmp_path / "tracked.txt"
    tracked_path.write_text("alpha", encoding="utf-8")
    project = _project_with_file(tracked_path)

    target = _build_target(
        project, path_text=str(tracked_path), lines=None, label="source"
    )

    assert target.file_id == "file-1"
    assert target.path is None


def test_fr_7_automatically_adds_untracked_paths(tmp_path: Path) -> None:
    """FR-7: untracked paths are automatically added to the project catalog."""

    untracked_path = tmp_path / "orphan.txt"
    untracked_path.write_text("beta", encoding="utf-8")
    project = Project()

    target = _build_target(
        project, path_text=str(untracked_path), lines=None, label="destination"
    )

    # Now the target should have a file_id because it was auto-added
    assert target.file_id is not None
    assert target.path is None

    # Verify it was added to the project
    entry = project.find_file_by_id(target.file_id)
    assert entry is not None
    assert entry["path"] == str(untracked_path)
