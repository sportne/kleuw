"""GUI tests for Kleuw's preferences dialog."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI
from tests._gui_stubs import StubRoot, build_stub_tk_module, build_stub_ttk_module


@pytest.mark.gui()
def test_open_preferences_dialog_creates_toplevel_window() -> None:
    """Verify that invoking the 'Preferences' action opens a dialog."""
    # Arrange
    mock_tk = build_stub_tk_module()
    mock_ttk = build_stub_ttk_module()
    stub_root = StubRoot()

    # Create a mock for the Toplevel widget instance
    mock_toplevel_instance = MagicMock(name="ToplevelInstance")

    # Replace the factory in the stub tk module with a mock that returns our instance
    mock_tk.Toplevel = MagicMock(
        name="ToplevelFactory", return_value=mock_toplevel_instance
    )

    gui = KleuwGUI(
        root=stub_root,
        tk_module=mock_tk,
        ttk_module=mock_ttk,
        messagebox_module=MagicMock(),
    )
    # Act
    action = gui._get_action_callback("Preferences")
    action()

    # Assert
    mock_tk.Toplevel.assert_called_once_with(gui.root)
    mock_toplevel_instance.title.assert_called_once_with("Preferences")
    mock_toplevel_instance.transient.assert_called_once_with(gui.root)
    mock_toplevel_instance.grab_set.assert_called_once()
