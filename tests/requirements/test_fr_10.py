"""Validation tests for FR-10 (line range selection per file)."""

from __future__ import annotations

from pathlib import Path

from kleuw.project import Project
from tests.requirements._gui_helpers import make_gui


def test_fr_10_line_selection_updates_summary(tmp_path: Path) -> None:
    """FR-10: Selecting line ranges updates each viewer independently."""

    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("one\ntwo\nthree")
    right_file.write_text("alpha\nbeta")
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

    gui._set_viewer_selection(gui._left_viewer, 2, 3)
    gui._set_viewer_selection(gui._right_viewer, 1, 1)

    assert gui._left_viewer.selection_start == 2
    assert gui._left_viewer.selection_end == 3
    assert gui._right_viewer.selection_start == 1
    assert gui._right_viewer.selection_end == 1
    summary = gui.selection_var.get()
    assert "Left L2–L3" in summary
    assert "Right L1" in summary
