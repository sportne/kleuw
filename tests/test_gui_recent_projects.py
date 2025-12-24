"""Tests for the 'Recent Projects' menu."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI
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
    )
    return gui, messagebox


def test_recent_projects_menu_initial_state(gui_stubs: SimpleNamespace) -> None:
    """The 'Recent Projects' menu should be empty initially."""
    gui, _ = _make_gui(gui_stubs)
    assert gui._recent_projects_menu is not None
    menu = gui._recent_projects_menu
    # Called once during __init__
    menu.delete.assert_called_once_with(0, "end")
    menu.add_command.assert_called_once_with(
        label="No recent projects", state="disabled"
    )


def test_opening_project_adds_to_recent_list(
    gui_stubs: SimpleNamespace, monkeypatch
) -> None:
    """Opening a new project should add it to the recent projects list."""
    gui, _ = _make_gui(gui_stubs)
    menu = gui._recent_projects_menu
    assert menu is not None

    # Reset mocks after initial setup
    menu.delete.reset_mock()
    menu.add_command.reset_mock()

    # Simulate opening a project by calling the method that adds to the recent list
    gui._add_to_recent_projects("/fake/project.json")

    assert gui._recent_projects == ["/fake/project.json"]

    # Check that the menu was cleared and the new item was added
    menu.delete.assert_called_once_with(0, "end")
    menu.add_command.assert_called_once()
    assert menu.add_command.call_args.kwargs["label"] == "/fake/project.json"

    # Reset again for the next check
    menu.delete.reset_mock()
    menu.add_command.reset_mock()

    # Simulate opening another project
    gui._add_to_recent_projects("/another/project.json")

    assert gui._recent_projects == ["/another/project.json", "/fake/project.json"]
    menu.delete.assert_called_once_with(0, "end")
    assert menu.add_command.call_count == 2

    # Check the labels of the calls
    labels = [call.kwargs["label"] for call in menu.add_command.call_args_list]
    assert labels == ["/another/project.json", "/fake/project.json"]


def test_recent_projects_list_is_capped(
    gui_stubs: SimpleNamespace, monkeypatch
) -> None:
    """The recent projects list should not exceed 10 items."""
    gui, _ = _make_gui(gui_stubs)
    for i in range(15):
        gui._add_to_recent_projects(f"/proj/{i}.json")

    assert len(gui._recent_projects) == 10
    assert gui._recent_projects[0] == "/proj/14.json"
    assert gui._recent_projects[-1] == "/proj/5.json"


def test_clicking_recent_project_opens_it(
    gui_stubs: SimpleNamespace, monkeypatch
) -> None:
    """Clicking a recent project menu item should open that project."""
    gui, _ = _make_gui(gui_stubs)
    open_recent_mock = MagicMock()
    monkeypatch.setattr(gui, "_open_recent_project", open_recent_mock)
    menu = gui._recent_projects_menu
    assert menu is not None

    # Add a recent project to populate the menu
    gui._add_to_recent_projects("/recent/project.json")

    # Extract the command from the mock's call arguments
    command = menu.add_command.call_args.kwargs["command"]

    # Call the command
    command()

    # Verify that _open_recent_project was called with the correct path
    open_recent_mock.assert_called_once_with("/recent/project.json")
