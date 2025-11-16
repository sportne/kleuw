"""Requirement validation tests for FR-16."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tests._gui_stubs import StubMessageBox, StubRoot
from tests.test_gui_files import _make_gui, _project_with_links


def test_fr_16_selecting_link_opens_files_and_regions(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """FR-16: Selecting a link opens its files and navigates to the region."""

    project, left_file, right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    gui._navigate_to_link_id("L1")

    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    assert gui._left_viewer.file_path == str(left_file)
    assert gui._left_viewer.selection_start == 2
    assert gui._left_viewer.selection_end == 3
    assert gui._right_viewer.file_path == str(right_file)
    assert gui._right_viewer.selection_start == 1
