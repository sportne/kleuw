"""Tests for GUI view options."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from kleuw.gui import KleuwGUI, _DEFAULT_FONT_SIZE, _MAX_FONT_SIZE, _MIN_FONT_SIZE
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


def test_increase_font_size(gui_stubs: SimpleNamespace) -> None:
    """Test that increasing font size updates the viewer widgets."""
    gui, _ = _make_gui(gui_stubs)
    initial_size = gui._font_size

    gui._increase_font_size()

    assert gui._font_size == initial_size + 1
    expected_font = ("TkFixedFont", initial_size + 1)

    assert gui._left_viewer is not None
    gui._left_viewer.text_widget.configure.assert_any_call(font=expected_font)
    gui._left_viewer.line_numbers_widget.configure.assert_any_call(font=expected_font)

    assert gui._right_viewer is not None
    gui._right_viewer.text_widget.configure.assert_any_call(font=expected_font)
    gui._right_viewer.line_numbers_widget.configure.assert_any_call(font=expected_font)


def test_decrease_font_size(gui_stubs: SimpleNamespace) -> None:
    """Test that decreasing font size updates the viewer widgets."""
    gui, _ = _make_gui(gui_stubs)
    initial_size = gui._font_size

    gui._decrease_font_size()

    assert gui._font_size == initial_size - 1
    expected_font = ("TkFixedFont", initial_size - 1)

    assert gui._left_viewer is not None
    gui._left_viewer.text_widget.configure.assert_any_call(font=expected_font)
    gui._left_viewer.line_numbers_widget.configure.assert_any_call(font=expected_font)

    assert gui._right_viewer is not None
    gui._right_viewer.text_widget.configure.assert_any_call(font=expected_font)
    gui._right_viewer.line_numbers_widget.configure.assert_any_call(font=expected_font)


def test_font_size_has_limits(gui_stubs: SimpleNamespace) -> None:
    """Test that font size cannot be increased or decreased beyond limits."""
    gui, _ = _make_gui(gui_stubs)
    gui._font_size = _MAX_FONT_SIZE

    gui._increase_font_size()
    assert gui._font_size == _MAX_FONT_SIZE

    gui._font_size = _MIN_FONT_SIZE
    gui._decrease_font_size()
    assert gui._font_size == _MIN_FONT_SIZE


def test_toggle_line_wrapping(gui_stubs: SimpleNamespace) -> None:
    """Test that toggling line wrapping updates the viewer widgets."""
    gui, _ = _make_gui(gui_stubs)
    tk = gui_stubs.tk

    assert not gui._line_wrapping_enabled

    # Enable wrapping
    gui._toggle_line_wrapping()
    assert gui._line_wrapping_enabled
    assert gui._left_viewer is not None
    gui._left_viewer.text_widget.configure.assert_called_with(wrap=tk.WORD)
    assert gui._right_viewer is not None
    gui._right_viewer.text_widget.configure.assert_called_with(wrap=tk.WORD)

    # Disable wrapping
    gui._toggle_line_wrapping()
    assert not gui._line_wrapping_enabled
    assert gui._left_viewer is not None
    gui._left_viewer.text_widget.configure.assert_called_with(wrap=tk.NONE)
    assert gui._right_viewer is not None
    gui._right_viewer.text_widget.configure.assert_called_with(wrap=tk.NONE)
