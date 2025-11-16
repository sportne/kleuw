"""Validation tests for FR-14 (region hash storage)."""

from __future__ import annotations

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.model import LinkType
from kleuw.project import Project
from tests.requirements._gui_helpers import make_gui


def test_fr_14_region_hashes_stored_for_both_targets(tmp_path: Path) -> None:
    """FR-14: Creating a link computes hashes for both endpoints."""

    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("alpha\nbeta\n")
    right_file.write_text("one\ntwo\n")
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
    gui._set_viewer_selection(gui._right_viewer, 2, 2)
    gui.relationship_var.set(LinkType.TESTS.value)
    gui._update_create_button_state()

    gui._create_link()

    assert len(project.links) == 1
    link = project.links[0]
    left_hash = compute_region_hash(str(left_file), start_line=1, end_line=2)
    right_hash = compute_region_hash(str(right_file), start_line=2, end_line=2)
    assert link["src"]["src_region_hash"] == {
        "algo": left_hash.algo,
        "value": left_hash.value,
    }
    assert link["dst"]["dst_region_hash"] == {
        "algo": right_hash.algo,
        "value": right_hash.value,
    }
