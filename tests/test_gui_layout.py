"""Tests for the Tkinter layout scaffolding."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI


class StubStringVar:
    """Minimal replacement for ``tkinter.StringVar``."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def set(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class StubRoot:
    """Headless replacement for ``tkinter.Tk``."""

    def __init__(self) -> None:
        self.config_kwargs: dict[str, Any] = {}
        self.bindings: list[tuple[str, Any]] = []

    def title(self, _title: str) -> None:  # pragma: no cover - trivial setter
        return None

    def geometry(self, _geometry: str) -> None:  # pragma: no cover - trivial setter
        return None

    def minsize(self, _width: int, _height: int) -> None:  # pragma: no cover
        return None

    def config(self, **kwargs: Any) -> None:
        self.config_kwargs.update(kwargs)

    def bind(self, sequence: str, handler: Any) -> None:
        self.bindings.append((sequence, handler))

    def mainloop(self) -> None:  # pragma: no cover - not exercised in tests
        return None


class StubMessageBox:
    """Records invocations instead of showing dialogs."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def showinfo(self, *, title: str, message: str) -> None:
        self.calls.append((title, message))


def _make_widget_factory(name: str) -> MagicMock:
    return MagicMock(name=name, side_effect=lambda *args, **kwargs: MagicMock())


@pytest.fixture()
def stub_tk_module() -> SimpleNamespace:
    module = SimpleNamespace()
    module.END = "end"
    module.BOTH = "both"
    module.LEFT = "left"
    module.RIGHT = "right"
    module.W = "west"
    module.TOP = "top"
    module.BOTTOM = "bottom"
    module.X = "x"
    module.Y = "y"
    module.VERTICAL = "vertical"
    module.HORIZONTAL = "horizontal"
    module.NONE = "none"
    module.DISABLED = "disabled"
    module.SUNKEN = "sunken"
    module.Menu = _make_widget_factory("Menu")
    module.Listbox = _make_widget_factory("Listbox")
    module.Text = _make_widget_factory("Text")
    module.Scrollbar = _make_widget_factory("Scrollbar")
    module.Toplevel = _make_widget_factory("Toplevel")
    module.StringVar = MagicMock(side_effect=lambda value="", **_: StubStringVar(value))
    return module


@pytest.fixture()
def stub_ttk_module() -> SimpleNamespace:
    module = SimpleNamespace()
    module.Frame = _make_widget_factory("Frame")
    module.Button = _make_widget_factory("Button")
    module.Label = _make_widget_factory("Label")
    module.PanedWindow = _make_widget_factory("PanedWindow")
    module.Scrollbar = _make_widget_factory("TtkScrollbar")
    module.Combobox = _make_widget_factory("Combobox")
    module.Treeview = _make_widget_factory("Treeview")
    module.Separator = _make_widget_factory("Separator")
    module.Style = MagicMock(side_effect=lambda *args, **kwargs: MagicMock())
    return module


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
    gui._placeholder_action("Headless Test")
    assert gui.selection_var.get() == "Action requested: Headless Test"
    assert stub_messagebox.calls[-1] == (
        "Kleuw",
        "Headless Test is not implemented yet.",
    )
    shortcut_bindings = {sequence for sequence, _ in root.bindings}
    assert "<Control-s>" in shortcut_bindings
