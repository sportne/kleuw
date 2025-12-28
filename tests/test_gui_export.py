"""Tests for the GUI's export summary functionality."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from kleuw.gui import KleuwGUI
from kleuw.project import Project
from tests._gui_stubs import (
    StubMessageBox,
    StubRoot,
    build_stub_tk_module,
    build_stub_ttk_module,
)


@pytest.fixture
def gui_stubs() -> SimpleNamespace:
    """Fixture for providing stubbed Tkinter modules."""
    return SimpleNamespace(tk=build_stub_tk_module(), ttk=build_stub_ttk_module())


def _make_gui(
    gui_stubs: SimpleNamespace,
    filedialog_module: SimpleNamespace | None = None,
    *,
    project: Project | None = None,
) -> tuple[KleuwGUI, StubMessageBox]:
    """Helper to create a KleuwGUI instance with stubbed dependencies."""
    messagebox = StubMessageBox()
    gui = KleuwGUI(
        root=StubRoot(),
        tk_module=gui_stubs.tk,
        ttk_module=gui_stubs.ttk,
        messagebox_module=messagebox,
        enable_tooltips=False,
        filedialog_module=filedialog_module,
        project=project,
    )
    return gui, messagebox


def test_export_summary_writes_to_file(
    gui_stubs: SimpleNamespace, tmp_path: Path
) -> None:
    """The 'Export Summary' action should write a summary to the selected file."""
    project = Project(
        files=[{"id": "F1", "path": "a.txt"}],
        links=[
            {
                "id": "L1",
                "type": "implements",
                "src": {"file_id": "F1"},
                "dst": {"path": "b.txt"},
            }
        ],
    )
    output_path = tmp_path / "summary.txt"
    filedialog = SimpleNamespace(asksaveasfilename=lambda **kwargs: str(output_path))
    gui, messagebox = _make_gui(
        gui_stubs, filedialog_module=filedialog, project=project
    )

    # Create dummy files for staleness check
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")

    gui._export_summary()

    assert output_path.exists()
    content = output_path.read_text()
    assert "Files:" in content
    assert "Links:" in content
    assert "Total links: 1" in content
    assert not messagebox.error_calls
