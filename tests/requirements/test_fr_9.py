"""Validation tests for FR-9 (side-by-side file viewing)."""

from __future__ import annotations

from pathlib import Path

from kleuw.project import Project
from tests.requirements._gui_helpers import make_gui


def test_fr_9_gui_displays_two_files_side_by_side(tmp_path: Path) -> None:
    """FR-9: GUI shall show two independently selected files simultaneously."""

    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("alpha\nbeta")
    right_file.write_text("one\ntwo")
    project = Project(
        files=[
            {"id": "left", "path": str(left_file)},
            {"id": "right", "path": str(right_file)},
        ]
    )
    gui, _ = make_gui(project=project)

    assert gui._left_viewer is not None and gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left_file))
    gui._load_file_into_viewer(gui._right_viewer, str(right_file))

    assert gui._left_viewer.file_path == str(left_file)
    assert gui._right_viewer.file_path == str(right_file)
    assert "Left Viewer" in gui._left_viewer.label_var.get()
    assert "Right Viewer" in gui._right_viewer.label_var.get()
    assert gui._left_viewer.text_widget.content.splitlines() == ["alpha", "beta"]
    assert gui._right_viewer.text_widget.content.splitlines() == ["one", "two"]
