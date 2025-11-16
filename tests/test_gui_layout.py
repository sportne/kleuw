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
