"""Shared test doubles for Tkinter-dependent tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

__all__ = [
    "StubStringVar",
    "StubRoot",
    "StubMessageBox",
    "build_stub_tk_module",
    "build_stub_ttk_module",
]


def _make_widget_factory(name: str) -> MagicMock:
    return MagicMock(name=name, side_effect=lambda *args, **kwargs: MagicMock())


class StubStringVar:
    """Minimal replacement for ``tkinter.StringVar``."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def set(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class StubRoot:
    """Headless replacement for ``tkinter.Tk`` used in tests."""

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
        self.info_calls: list[tuple[str, str]] = []
        self.error_calls: list[tuple[str, str]] = []

    def showinfo(self, *, title: str, message: str) -> None:
        self.info_calls.append((title, message))

    def showerror(self, *, title: str, message: str) -> None:
        self.error_calls.append((title, message))

    def askyesno(self, *, title: str, message: str) -> bool:
        return getattr(self, "askyesno_response", False)


def build_stub_tk_module() -> SimpleNamespace:
    """Return a Tkinter-like namespace compatible with ``KleuwGUI``."""

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
    module.NORMAL = "normal"
    module.SUNKEN = "sunken"
    module.Menu = _make_widget_factory("Menu")
    module.Listbox = _make_widget_factory("Listbox")
    module.Text = _make_widget_factory("Text")
    module.Scrollbar = _make_widget_factory("Scrollbar")
    module.Toplevel = _make_widget_factory("Toplevel")
    module.StringVar = MagicMock(side_effect=lambda value="", **_: StubStringVar(value))
    return module


def build_stub_ttk_module() -> SimpleNamespace:
    """Return a ttk-like namespace compatible with ``KleuwGUI``."""

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
