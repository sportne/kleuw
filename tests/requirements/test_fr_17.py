"""Requirement validation tests for FR-17."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kleuw.model import LinkType
from tests._gui_stubs import StubMessageBox, StubRoot
from tests.test_gui_files import _make_gui, _project_with_links


def test_fr_17_editing_link_metadata_updates_project(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """FR-17: Users can edit link type, notes, and tags."""

    project, _left_file, _right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    gui._apply_link_edit(
        "L1",
        type_value=LinkType.DEFINES.value,
        tags_text="tag-one, tag-two",
        note_text=" updated note ",
    )

    updated = project.find_link_by_id("L1")
    assert updated is not None
    assert updated["type"] == LinkType.DEFINES.value
    assert updated["tags"] == ["tag-one", "tag-two"]
    assert updated["note"] == "updated note"
