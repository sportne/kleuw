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


def _create_fake_menu(*_args: Any, **_kwargs: Any) -> MagicMock:
    """Factory for a MagicMock that quacks like a Tkinter menu."""
    menu = MagicMock(name="FakeMenu")
    menu.delete = MagicMock(name="menu.delete")
    menu.add_command = MagicMock(name="menu.add_command")
    menu.add_cascade = MagicMock(name="menu.add_cascade")
    menu.add_separator = MagicMock(name="menu.add_separator")
    return menu


def _create_fake_paned_window(*_args: Any, **_kwargs: Any) -> MagicMock:
    """Factory for a MagicMock that quacks like a Tkinter PanedWindow."""
    window = MagicMock(name="FakePanedWindow")
    _internal_panes: list[str] = []

    def _panes_method() -> list[str]:
        return _internal_panes.copy()

    def _add_method(widget: Any, **_kwargs: Any) -> None:
        _internal_panes.append(str(widget))

    def _insert_method(index: int, widget: Any, **_kwargs: Any) -> None:
        _internal_panes.insert(index, str(widget))

    def _remove_method(widget: Any) -> None:
        try:
            _internal_panes.remove(str(widget))
        except ValueError:
            pass  # Mimic Tkinter's behavior for unknown panes

    window.panes = MagicMock(name="panes", side_effect=_panes_method)
    window.add = MagicMock(name="add", side_effect=_add_method)
    window.insert = MagicMock(name="insert", side_effect=_insert_method)
    window.remove = MagicMock(name="remove", side_effect=_remove_method)
    return window


class StubStringVar:
    """Minimal replacement for ``tkinter.StringVar``."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def set(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class StubIntVar:
    """Minimal replacement for ``tkinter.IntVar``."""

    def __init__(self, value: int = 0) -> None:
        self._value = value

    def set(self, value: int) -> None:
        self._value = value

    def get(self) -> int:
        return self._value


class StubBooleanVar:
    """Minimal replacement for ``tkinter.BooleanVar``."""

    def __init__(self, value: bool = False) -> None:
        self._value = value

    def set(self, value: bool) -> None:
        self._value = value

    def get(self) -> bool:
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

    def protocol(self, name: str, handler: Any) -> None:
        self.bindings.append((name, handler))

    def mainloop(self) -> None:  # pragma: no cover - not exercised in tests
        return None


class StubMessageBox:
    """Records invocations instead of showing dialogs."""

    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str]] = []
        self.error_calls: list[tuple[str, str]] = []
        self.warning_calls: list[tuple[str, str]] = []

    def showinfo(self, *, title: str, message: str) -> None:
        self.info_calls.append((title, message))

    def showwarning(self, *, title: str, message: str) -> None:
        self.warning_calls.append((title, message))

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
    module.E = "east"
    module.TOP = "top"
    module.BOTTOM = "bottom"
    module.X = "x"
    module.Y = "y"
    module.VERTICAL = "vertical"
    module.HORIZONTAL = "horizontal"
    module.NONE = "none"
    module.WORD = "word"
    module.DISABLED = "disabled"
    module.NORMAL = "normal"
    module.SUNKEN = "sunken"
    module.Menu = MagicMock(name="Menu", side_effect=_create_fake_menu)
    module.Listbox = _make_widget_factory("Listbox")
    text_widget_mock = MagicMock()
    text_widget_mock.get.return_value = "hello\nworld"
    text_widget_mock.cget.return_value = "disabled"
    module.Text = MagicMock(return_value=text_widget_mock)
    module.Scrollbar = _make_widget_factory("Scrollbar")
    module.Toplevel = _make_widget_factory("Toplevel")
    module.StringVar = MagicMock(side_effect=lambda value="", **_: StubStringVar(value))
    module.IntVar = MagicMock(side_effect=lambda value=0, **_: StubIntVar(value))
    module.BooleanVar = MagicMock(
        side_effect=lambda value=False, **_: StubBooleanVar(value)
    )
    module.Tk = MagicMock(side_effect=lambda **_: StubRoot())
    return module


def build_stub_ttk_module() -> SimpleNamespace:
    """Return a ttk-like namespace compatible with ``KleuwGUI``."""

    module = SimpleNamespace()
    module.Frame = _make_widget_factory("Frame")
    module.Button = _make_widget_factory("Button")
    module.Label = _make_widget_factory("Label")
    module.PanedWindow = MagicMock(
        name="PanedWindow", side_effect=_create_fake_paned_window
    )
    module.Scrollbar = _make_widget_factory("TtkScrollbar")
    module.Combobox = _make_widget_factory("Combobox")
    module.Treeview = _make_widget_factory("Treeview")
    module.Separator = _make_widget_factory("Separator")
    module.Style = MagicMock(side_effect=lambda *args, **kwargs: MagicMock())
    module.Entry = _make_widget_factory("Entry")
    module.Spinbox = _make_widget_factory("Spinbox")
    module.Checkbutton = _make_widget_factory("Checkbutton")
    return module
