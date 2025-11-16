"""Validation tests for FR-12 (whole-file relationships)."""

from __future__ import annotations

from pathlib import Path

from kleuw.model import LinkType
from kleuw.project import Project
from tests.requirements._gui_helpers import make_gui


def test_fr_12_whole_file_relationship_when_no_selection(tmp_path: Path) -> None:
    """FR-12: Unselected viewers create whole-file targets when linking."""

    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("source-1\nsource-2")
    right_file.write_text("dest-1\ndest-2")
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
    gui._set_viewer_selection(gui._left_viewer, 1, 2)
    gui.relationship_var.set(LinkType.REFERS_TO.value)
    gui._update_create_button_state()

    gui._create_link()

    assert len(project.links) == 1
    link = project.links[0]
    assert "lines" in link["src"]
    assert "lines" not in link["dst"]
