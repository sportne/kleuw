"""Requirement validation tests for FR-15."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kleuw.model import LineSpan, Link, LinkType, Target
from tests._gui_stubs import StubMessageBox, StubRoot
from tests.test_gui_files import _make_gui, _project_with_links


def test_fr_15_links_panel_displays_all_links(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """FR-15: The GUI shall display all links in a tabular list."""

    project, left_file, right_file = _project_with_links(tmp_path)
    project.add_link(
        Link(
            id="L2",
            type=LinkType.DEPENDS_ON,
            src=Target(file_id="src", lines=LineSpan(start=1, end=2)),
            dst=Target(file_id="dst", lines=LineSpan(start=1, end=1)),
        )
    )
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    assert gui._links_tree is not None
    assert set(gui._links_tree.get_children()) == {"L1", "L2"}
    row = gui._links_tree.items["L2"]  # type: ignore[index]
    assert row[0] == "L2" and row[1] == LinkType.DEPENDS_ON.value
    assert row[2] == f"{left_file} L1–L2"
    assert row[3] == f"{right_file} L1"
