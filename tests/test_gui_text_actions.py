from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from kleuw.gui import KleuwGUI
from tests._gui_stubs import (
    StubRoot,
    build_stub_messagebox_module,
    build_stub_tk_module,
    build_stub_ttk_module,
)


def test_select_all_text_invokes_tag_add_for_selection(tmp_path: Path) -> None:
    """Verify that the 'select all' action adds the 'SEL' tag to the whole text."""
    # Setup
    tk_module = build_stub_tk_module()
    messagebox_stub = build_stub_messagebox_module()
    file_path = tmp_path / "file1.txt"
    file_path.write_text("hello\nworld")
    sut = KleuwGUI(
        root=StubRoot(),
        tk_module=tk_module,
        ttk_module=build_stub_ttk_module(),
        messagebox_module=messagebox_stub,
        enable_tooltips=False,
    )
    sut._load_file_into_viewer(sut._left_viewer, str(file_path))
    sut._left_viewer.text_widget.tag_add = MagicMock()
    mock_event = MagicMock()
    mock_event.widget = sut._left_viewer.text_widget

    # Action
    sut._select_all_text(mock_event)

    # Verification
    sut._left_viewer.text_widget.tag_add.assert_called_once_with(
        tk_module.SEL, "1.0", tk_module.END
    )
    assert not messagebox_stub.error_calls
