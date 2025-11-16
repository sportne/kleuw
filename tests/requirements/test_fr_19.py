"""Requirement validation tests for FR-19."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tests._gui_stubs import StubMessageBox, StubRoot
from tests.test_gui_files import _make_gui, _project_with_links


def test_fr_19_delete_link_removes_entry_and_row(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """FR-19: Users can delete links from the project via the GUI."""

    project, _left_file, _right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    assert gui._links_tree is not None

    gui._links_tree.selection_set("L1")  # type: ignore[union-attr]
    gui._delete_selected_links()

    assert project.links == []
    assert gui._links_tree.get_children() == ()
