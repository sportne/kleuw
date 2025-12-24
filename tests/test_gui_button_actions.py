"""Tests for GUI button actions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
    gui_stubs: SimpleNamespace, monkeypatch: Any
) -> None:
    """The 'Edit Link' action should open the edit dialog for the selected link."""
    project = Project(
        links=[
            {
                "id": "L1",
                "type": "implements",
                "src": {"path": "a"},
                "dst": {"path": "b"},
            }
        ]
    )
    gui, _ = _make_gui(gui_stubs, project=project)

    # Mock the dialog opening method
    dialog_opened = False

    def mock_open_edit_dialog(link_entry: Any) -> None:
        nonlocal dialog_opened
        dialog_opened = True

    monkeypatch.setattr(gui, "_open_edit_dialog", mock_open_edit_dialog)

    # Simulate selecting a link
    assert gui._links_tree is not None
    gui._links_tree.selection.return_value = ("L1",)

    gui._edit_selected_link()

    assert dialog_opened


def test_undo_redo_create_link(
    gui_stubs: SimpleNamespace, monkeypatch: Any, tmp_path: Path
) -> None:
    """Test undoing and redoing a create link action."""
    project = Project()
    gui, messagebox = _make_gui(gui_stubs, project=project)

    left_file = tmp_path / "a.txt"
    right_file = tmp_path / "b.txt"
    left_file.write_text("a")
    right_file.write_text("b")

    # Mock the necessary UI components and state for creating a link
    gui._left_viewer.file_path = str(left_file)
    gui._right_viewer.file_path = str(right_file)
    gui.relationship_var.set("implements")
    gui._left_viewer.selection_start = 1
    gui._right_viewer.selection_start = 1
    gui._left_viewer.line_count = 1
    gui._right_viewer.line_count = 1

    assert len(project.links) == 0

    # Create a link
    gui._create_link()
    assert not messagebox.error_calls, " ".join(
        str(call) for call in messagebox.error_calls
    )
    assert len(project.links) == 1
    link_id = project.links[0]["id"]

    # Undo the link creation
    gui._undo()
    assert len(project.links) == 0
    assert project.find_link_by_id(link_id) is None

    # Redo the link creation
    gui._redo()
    assert len(project.links) == 1
    assert project.find_link_by_id(link_id) is not None


def test_create_link_with_duplicate_id_shows_error(
    gui_stubs: SimpleNamespace, monkeypatch: Any, tmp_path: Path
) -> None:
    """Test that creating a link with a duplicate ID shows an error."""
    project = Project(
        links=[
            {
                "id": "link-1",
                "type": "implements",
                "src": {"path": "a"},
                "dst": {"path": "b"},
            }
        ]
    )
    gui, messagebox = _make_gui(gui_stubs, project=project)

    left_file = tmp_path / "a.txt"
    right_file = tmp_path / "b.txt"
    left_file.write_text("a")
    right_file.write_text("b")

    # Mock the necessary UI components and state for creating a link
    gui._left_viewer.file_path = str(left_file)
    gui._right_viewer.file_path = str(right_file)
    gui.relationship_var.set("implements")
    gui._left_viewer.selection_start = 1
    gui._right_viewer.selection_start = 1
    gui._left_viewer.line_count = 1
    gui._right_viewer.line_count = 1

    monkeypatch.setattr(gui, "_generate_link_id", lambda: "link-1")

    # Create a link
    gui._create_link()

    assert len(messagebox.error_calls) == 1
    assert "already exists" in messagebox.error_calls[0][1]


def test_delete_link_undo_redo(gui_stubs: SimpleNamespace) -> None:
    """Test deleting a link and then undoing and redoing the action."""
    project = Project(
        links=[
            {
                "id": "L1",
                "type": "implements",
                "src": {"path": "a"},
                "dst": {"path": "b"},
            }
        ]
    )
    gui, _ = _make_gui(gui_stubs, project=project)

    assert len(project.links) == 1

    # Simulate selecting the link
    assert gui._links_tree is not None
    gui._links_tree.selection.return_value = ("L1",)

    # Delete the link
    gui._delete_selected_links()
    assert len(project.links) == 0

    # Undo the deletion
    gui._undo()
    assert len(project.links) == 1
    assert project.find_link_by_id("L1") is not None

    # Redo the deletion
    gui._redo()
    assert len(project.links) == 0
    assert project.find_link_by_id("L1") is None
