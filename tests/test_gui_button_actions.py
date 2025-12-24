"""Tests for GUI button actions."""

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


def test_add_files_calls_file_dialog(gui_stubs: SimpleNamespace) -> None:
    """The 'Add File' action should open a file dialog."""
    filedialog_calls = []

    def _mock_askopenfilenames(**kwargs: str) -> list[str]:
        filedialog_calls.append(kwargs)
        return []

    filedialog = SimpleNamespace(askopenfilenames=_mock_askopenfilenames)
    gui, _ = _make_gui(gui_stubs, filedialog)

    gui._add_files()

    assert len(filedialog_calls) == 1
    assert "title" in filedialog_calls[0]


def test_check_staleness_with_no_links(gui_stubs: SimpleNamespace) -> None:
    """'Check Staleness' should handle projects with no links gracefully."""
    project = Project()
    gui, messagebox = _make_gui(gui_stubs, project=project)

    gui._run_staleness_check()

    # The staleness dialog should still appear with a summary.
    # We can't easily inspect the dialog's content with the current stubs,
    # but we can check that no error was shown.
    assert not messagebox.error_calls


def test_remove_selected_files_removes_from_listbox(
    gui_stubs: SimpleNamespace,
) -> None:
    """The 'Remove File' action should remove the selected file from the list."""
    gui, _ = _make_gui(gui_stubs)

    # Manually add files to the listbox and internal list
    gui._files = ["a.txt", "b.txt"]
    assert gui._file_listbox is not None
    gui._file_listbox.insert("end", "a.txt")
    gui._file_listbox.insert("end", "b.txt")

    # Simulate selecting the first file
    gui._file_listbox.curselection.return_value = ("0",)

    gui._remove_selected_files()

    assert gui._files == ["b.txt"]
    gui._file_listbox.delete.assert_called_with(0)


def test_edit_selected_link_opens_dialog(
    gui_stubs: SimpleNamespace, monkeypatch
) -> None:
    """The 'Edit Link' action should open the edit dialog for the selected link."""
    project = Project(
        links=[{"id": "L1", "type": "implements", "src": {"path": "a"}, "dst": {"path": "b"}}]
    )
    gui, _ = _make_gui(gui_stubs, project=project)

    # Mock the dialog opening method
    dialog_opened = False
    def mock_open_edit_dialog(link_entry):
        nonlocal dialog_opened
        dialog_opened = True

    monkeypatch.setattr(gui, "_open_edit_dialog", mock_open_edit_dialog)

    # Simulate selecting a link
    assert gui._links_tree is not None
    gui._links_tree.selection.return_value = ("L1",)

    gui._edit_selected_link()

    assert dialog_opened
