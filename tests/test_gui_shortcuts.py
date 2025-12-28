"""Tests for GUI keyboard shortcuts."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI

from ._gui_stubs import (
    StubRoot,
    build_stub_filedialog_module,
    build_stub_messagebox_module,
    build_stub_tk_module,
    build_stub_ttk_module,
)


@pytest.mark.parametrize(
    "sequence, action_name",
    [
        ("<Control-Shift-S>", "_save_project_as"),
        ("<Control-z>", "_undo"),
        ("<Control-y>", "_redo"),
        ("<Control-Shift-Z>", "_redo"),
        ("<Delete>", "_delete_selected_links"),
        ("<F2>", "_edit_selected_link"),
        ("<Control-Shift-C>", "_recompute_hashes"),
        ("<Control-Shift-V>", "_validate_project"),
        ("<Control-e>", "_export_summary"),
    ],
)
def test_keyboard_shortcuts_trigger_correct_actions(
    monkeypatch: Any, sequence: str, action_name: str
) -> None:
    """Verify that keyboard shortcuts trigger the expected GUI actions."""
    root = StubRoot()
    messagebox = build_stub_messagebox_module()
    filedialog = build_stub_filedialog_module()

    mock_action = MagicMock()
    monkeypatch.setattr(KleuwGUI, action_name, mock_action)

    app = KleuwGUI(
        root=root,
        tk_module=build_stub_tk_module(),
        ttk_module=build_stub_ttk_module(),
        messagebox_module=messagebox,
        filedialog_module=filedialog,
    )
    app.root.event_generate(sequence)

    assert mock_action.call_count == 1
