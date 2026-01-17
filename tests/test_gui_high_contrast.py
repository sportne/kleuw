"""Tests for GUI high contrast mode."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from kleuw.gui import _THEME_HIGH_CONTRAST, KleuwGUI
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
) -> tuple[KleuwGUI, StubMessageBox]:
    """Helper to create a KleuwGUI instance with stubbed dependencies."""
    messagebox = StubMessageBox()
    gui = KleuwGUI(
        root=StubRoot(),
        tk_module=gui_stubs.tk,
        ttk_module=gui_stubs.ttk,
        messagebox_module=messagebox,
        enable_tooltips=False,
    )
    return gui, messagebox


def test_high_contrast_recolors_files_panel(gui_stubs: SimpleNamespace) -> None:
    """Test that toggling high contrast mode recolors the 'Project Files' listbox."""
    gui, _ = _make_gui(gui_stubs)

    # Initial state: high contrast disabled
    assert not gui._high_contrast_enabled

    # Enable high contrast
    gui._toggle_high_contrast()
    assert gui._high_contrast_enabled

    # Verify that self._file_listbox was configured with high contrast colors
    assert gui._file_listbox is not None
    gui._file_listbox.configure.assert_any_call(
        background=_THEME_HIGH_CONTRAST["bg"],
        foreground=_THEME_HIGH_CONTRAST["fg"],
        selectbackground=_THEME_HIGH_CONTRAST["select_bg"],
        selectforeground=_THEME_HIGH_CONTRAST["select_fg"],
    )


def test_high_contrast_recolors_selection_summary(gui_stubs: SimpleNamespace) -> None:
    """Test that toggling high contrast mode recolors the selection summary label."""
    gui, _ = _make_gui(gui_stubs)

    # Enable high contrast
    gui._toggle_high_contrast()

    # Verify that self._selection_summary_label was configured with high contrast colors
    assert gui._selection_summary_label is not None
    gui._selection_summary_label.configure.assert_any_call(
        background=_THEME_HIGH_CONTRAST["bg"],
        foreground=_THEME_HIGH_CONTRAST["fg"],
    )
