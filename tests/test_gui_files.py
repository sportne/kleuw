"""Tests for file loading behavior in the Kleuw GUI viewers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kleuw.gui import KleuwGUI
from tests._gui_stubs import StubMessageBox, StubRoot, StubStringVar


class _BaseWidget:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._bindings: dict[str, Callable[..., Any]] = {}

    def pack(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - layout helper
        return None

    def bind(self, sequence: str, callback: Callable[..., Any]) -> None:
        self._bindings[sequence] = callback

    def destroy(self) -> None:  # pragma: no cover - tooltip helper
        return None


class _FakeMenu(_BaseWidget):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        super().__init__()
        self.commands: list[tuple[str | None, Callable[..., Any] | None]] = []

    def add_command(self, *, label: str, command: Callable[..., Any]) -> None:
        self.commands.append((label, command))

    def add_separator(self) -> None:
        self.commands.append((None, None))

    def add_cascade(self, *, label: str, menu: Any) -> None:
        self.commands.append((label, menu))


class _FakeListbox(_BaseWidget):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        super().__init__()
        self.items: list[str] = []
        self._selection: tuple[int, ...] = ()

    def insert(self, index: str | int, value: str) -> None:
        if index == "end":
            self.items.append(value)
        else:
            self.items.insert(int(index), value)

    def delete(self, start: int, end: int | str | None = None) -> None:
        if end is None or end == start:
            del self.items[int(start)]
        elif end == "end":
            del self.items[int(start) :]
        else:
            del self.items[int(start) : int(end) + 1]

    def curselection(self) -> tuple[int, ...]:
        return self._selection

    def selection_set(self, index: int) -> None:
        self._selection = (int(index),)

    def size(self) -> int:
        return len(self.items)


class _FakeText(_BaseWidget):
    def __init__(self, *_args: Any, state: str = "normal", **_kwargs: Any) -> None:
        super().__init__()
        self.state = state
        self.content = ""
        self.last_scroll: tuple[Any, ...] | None = None
        self.width = 0
        self.yscrollcommand: Callable[..., Any] | None = None
        self.xscrollcommand: Callable[..., Any] | None = None

    def configure(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "yscrollcommand" in kwargs:
            self.yscrollcommand = kwargs["yscrollcommand"]
        if "xscrollcommand" in kwargs:
            self.xscrollcommand = kwargs["xscrollcommand"]
        if "width" in kwargs:
            self.width = kwargs["width"]

    config = configure

    def delete(self, *_args: Any, **_kwargs: Any) -> None:
        self.content = ""

    def insert(self, *_args: Any, **kwargs: Any) -> None:
        text = kwargs.get("text")
        if text is None and len(_args) >= 2:
            text = _args[1]
        if text is None:
            text = ""
        self.content = str(text)

    def get(self, *_args: Any, **_kwargs: Any) -> str:
        return self.content

    def yview(self, *args: Any) -> None:
        self.last_scroll = args

    def yview_moveto(self, fraction: Any) -> None:
        self.last_scroll = ("moveto", fraction)

    def xview(self, *args: Any) -> None:
        self.last_scroll = args

    def xview_moveto(self, fraction: Any) -> None:
        self.last_scroll = ("x-moveto", fraction)

    def see(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeScrollbar(_BaseWidget):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        super().__init__()
        self.command: Callable[..., Any] | None = None
        self.last_set: tuple[str, str] | None = None

    def configure(self, **kwargs: Any) -> None:
        if "command" in kwargs:
            self.command = kwargs["command"]

    config = configure

    def set(self, first: str, last: str) -> None:
        self.last_set = (first, last)


class _FakePanedWindow(_BaseWidget):
    def __init__(self, *_args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.items: list[tuple[Any, dict[str, Any]]] = []

    def add(self, child: Any, **kwargs: Any) -> None:
        self.items.append((child, kwargs))


class _FakeFrame(_BaseWidget):
    pass


class _FakeLabel(_BaseWidget):
    def __init__(
        self,
        *_args: Any,
        text: str | None = None,
        textvariable: StubStringVar | None = None,
        **_kwargs: Any,
    ) -> None:
        super().__init__()
        self.text = text
        self.textvariable = textvariable


class _FakeButton(_BaseWidget):
    def __init__(
        self, *_args: Any, command: Callable[..., Any] | None = None, **_kwargs: Any
    ) -> None:
        super().__init__()
        self.command = command

    def invoke(self) -> None:
        if self.command is not None:
            self.command()


class _FakeCombobox(_BaseWidget):
    def __init__(
        self,
        *_args: Any,
        values: tuple[str, ...] | list[str] | None = None,
        textvariable: StubStringVar | None = None,
        **_kwargs: Any,
    ) -> None:
        super().__init__()
        self.values = tuple(values or ())
        self.textvariable = textvariable


class _FakeTreeview(_BaseWidget):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        super().__init__()
        self.rows: list[tuple[str, ...]] = []
        self.yscrollcommand: Callable[..., Any] | None = None
        self.last_yview: tuple[Any, ...] | None = None

    def heading(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def column(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def configure(self, **kwargs: Any) -> None:
        if "yscrollcommand" in kwargs:
            self.yscrollcommand = kwargs["yscrollcommand"]

    config = configure

    def insert(self, *_args: Any, values: tuple[str, ...]) -> None:
        self.rows.append(values)

    def yview(self, *args: Any) -> None:
        self.last_yview = args


class _FakeSeparator(_BaseWidget):
    pass


class _FakeStyle:
    def configure(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - trivial
        return None


class _FakeToplevel(_BaseWidget):
    def wm_overrideredirect(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - tooltip helper
        return None

    def wm_geometry(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - tooltip helper
        return None


@pytest.fixture()
def functional_tk_module() -> SimpleNamespace:
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
    module.Menu = _FakeMenu
    module.Listbox = _FakeListbox
    module.Text = _FakeText
    module.Scrollbar = _FakeScrollbar
    module.Toplevel = _FakeToplevel
    module.StringVar = lambda value="", **_: StubStringVar(value)  # type: ignore[assignment]
    return module


@pytest.fixture()
def functional_ttk_module() -> SimpleNamespace:
    module = SimpleNamespace()
    module.Frame = _FakeFrame
    module.Button = _FakeButton
    module.Label = _FakeLabel
    module.PanedWindow = _FakePanedWindow
    module.Scrollbar = _FakeScrollbar
    module.Combobox = _FakeCombobox
    module.Treeview = _FakeTreeview
    module.Separator = _FakeSeparator
    module.Style = lambda *args, **kwargs: _FakeStyle()
    return module


@pytest.fixture()
def stub_messagebox() -> StubMessageBox:
    return StubMessageBox()


@pytest.fixture()
def stub_filedialog() -> SimpleNamespace:
    return SimpleNamespace(askopenfilenames=lambda **_: ())


def _make_gui(
    stub_root: StubRoot,
    tk_module: SimpleNamespace,
    ttk_module: SimpleNamespace,
    messagebox: StubMessageBox,
    filedialog_module: SimpleNamespace,
) -> KleuwGUI:
    return KleuwGUI(
        root=stub_root,
        tk_module=tk_module,
        ttk_module=ttk_module,
        messagebox_module=messagebox,
        enable_tooltips=False,
        filedialog_module=filedialog_module,
    )


def test_add_files_uses_dialog_and_populates_listbox(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("alpha")
    file_b.write_text("beta")
    filedialog_calls: list[dict[str, Any]] = []

    def _askopenfilenames(**kwargs: Any) -> tuple[str, ...]:
        filedialog_calls.append(kwargs)
        return (str(file_a), str(file_b), str(file_a))

    filedialog = SimpleNamespace(askopenfilenames=_askopenfilenames)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )

    gui._add_files()

    assert gui._files == [str(file_a), str(file_b)]
    assert gui._file_listbox is not None
    assert gui._file_listbox.items == [str(file_a), str(file_b)]  # type: ignore[union-attr]
    assert filedialog_calls[-1]["title"].startswith("Add")


def test_open_selected_file_loads_left_viewer(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("one\r\ntwo\nthree")
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )

    gui._files.extend([str(file_path)])
    assert gui._file_listbox is not None
    gui._file_listbox.items.append(str(file_path))  # type: ignore[union-attr]
    gui._file_listbox.selection_set(0)  # type: ignore[union-attr]

    gui._open_selection_in_viewer("left")

    viewer = gui._left_viewer
    assert viewer is not None
    assert viewer.file_path == str(file_path)
    assert viewer.label_var.get().endswith(str(file_path))
    assert viewer.text_widget.content == "one\ntwo\nthree"
    assert viewer.line_numbers_widget.content.splitlines() == ["1", "2", "3"]


def test_missing_file_reports_error(
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )
    missing = "/tmp/does-not-exist.txt"
    gui._files.append(missing)
    assert gui._file_listbox is not None
    gui._file_listbox.items.append(missing)  # type: ignore[union-attr]
    gui._file_listbox.selection_set(0)  # type: ignore[union-attr]

    gui._open_selection_in_viewer("right")

    assert stub_messagebox.error_calls[-1][1].startswith("Could not open")
