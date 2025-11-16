"""Validation tests for FR-13 (unique link identifiers)."""

from __future__ import annotations

from pathlib import Path

from kleuw.model import LinkType
from kleuw.project import Project
from tests.requirements._gui_helpers import make_gui


def test_fr_13_unique_link_ids_are_generated(tmp_path: Path) -> None:
    """FR-13: Each created link receives a unique ``link-<n>`` identifier."""

    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("source")
    right_file.write_text("dest")
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
    gui._set_viewer_selection(gui._left_viewer, 1, 1)
    gui._set_viewer_selection(gui._right_viewer, 1, 1)
    gui.relationship_var.set(LinkType.DEPENDS_ON.value)
    gui._update_create_button_state()

    gui._create_link()
    gui._create_link()

    assert [link["id"] for link in project.links] == ["link-1", "link-2"]
