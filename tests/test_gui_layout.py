"""Tests for the Tkinter layout scaffolding."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from kleuw.gui import KleuwGUI
from tests._gui_stubs import (
    StubMessageBox,
    StubRoot,
    build_stub_tk_module,
    build_stub_ttk_module,
)


@pytest.fixture()
def stub_tk_module() -> SimpleNamespace:
    return build_stub_tk_module()


@pytest.fixture()
def stub_ttk_module() -> SimpleNamespace:
    return build_stub_ttk_module()


@pytest.fixture()
def stub_messagebox() -> StubMessageBox:
    return StubMessageBox()


def test_gui_builds_layout_with_stubs(
    stub_tk_module: SimpleNamespace,
    stub_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """The GUI shell should build without needing a real display."""

    root = StubRoot()
    gui = KleuwGUI(
        root=root,
        tk_module=stub_tk_module,
        ttk_module=stub_ttk_module,
        messagebox_module=stub_messagebox,
        enable_tooltips=False,
    )

    assert "menu" in root.config_kwargs
    initial_summary = gui.selection_var.get()
    gui._placeholder_action("Headless Test")
    assert gui.selection_var.get() == initial_summary
    assert stub_messagebox.info_calls[-1] == (
        "Kleuw",
        "Headless Test is not implemented yet.",
    )
    shortcut_bindings = {sequence for sequence, _ in root.bindings}
    assert "<Control-s>" in shortcut_bindings


def test_gui_toggles_files_panel_visibility(
    stub_tk_module: SimpleNamespace,
    stub_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    """The files panel should be hidden and shown when toggled."""

    root = StubRoot()
    gui = KleuwGUI(
        root=root,
        tk_module=stub_tk_module,
        ttk_module=stub_ttk_module,
        messagebox_module=stub_messagebox,
        enable_tooltips=False,
    )

    upper_paned_window = gui._upper_paned_window
    assert upper_paned_window is not None
    files_frame = gui._files_frame
    assert files_frame is not None

    # Initially, the files panel should be present.
    initial_panes = upper_paned_window.panes()
    assert str(files_frame) in initial_panes
    assert len(initial_panes) == 2

    # Hide the panel.
    gui._toggle_files_panel()
    panes_after_hide = upper_paned_window.panes()
    assert str(files_frame) not in panes_after_hide
    assert len(panes_after_hide) == 1

    # Show the panel again.
    gui._toggle_files_panel()
    panes_after_show = upper_paned_window.panes()
    assert str(files_frame) in panes_after_show
    assert len(panes_after_show) == 2
    assert panes_after_show[0] == str(files_frame)
