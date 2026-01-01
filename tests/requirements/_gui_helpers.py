"""Shared GUI test scaffolding for requirement validation tests."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from kleuw.gui import KleuwGUI
from kleuw.project import Project
from tests._gui_stubs import (
    StubBooleanVar,
    StubMessageBox,
    StubRoot,
    StubStringVar,
    _create_fake_menu,
)
from tests.test_gui_files import (
    _FakeButton,
    _FakeCheckbutton,
    _FakeCombobox,
    _FakeEntry,
    _FakeFrame,
    _FakeLabel,
    _FakeListbox,
    _FakePanedWindow,
    _FakeScrollbar,
    _FakeSeparator,
    _FakeStyle,
    _FakeText,
    _FakeToplevel,
    _FakeTreeview,
)


def build_functional_tk_module() -> SimpleNamespace:
    """Return a tk-like module backed by lightweight fake widgets."""

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
    module.DISABLED = "disabled"
    module.NORMAL = "normal"
    module.SUNKEN = "sunken"
    module.Menu = MagicMock(name="Menu", side_effect=_create_fake_menu)
    module.Listbox = _FakeListbox
    module.Text = _FakeText
    module.Scrollbar = _FakeScrollbar
    module.Toplevel = _FakeToplevel
    module.StringVar = _make_string_var_factory()
    module.BooleanVar = _make_boolean_var_factory()
    return module


def build_functional_ttk_module() -> SimpleNamespace:
    """Return a ttk-like module backed by fake widgets."""

    module = SimpleNamespace()
    module.Frame = _FakeFrame
    module.Button = _FakeButton
    module.Button.instances = []  # type: ignore[attr-defined]
    module.Label = _FakeLabel
    module.PanedWindow = _FakePanedWindow
    module.Scrollbar = _FakeScrollbar
    module.Combobox = _FakeCombobox
    module.Treeview = _FakeTreeview
    module.Separator = _FakeSeparator
    module.Entry = _FakeEntry
    module.Checkbutton = _FakeCheckbutton
    module.Style = lambda *args, **kwargs: _FakeStyle()  # type: ignore[assignment]
    return module


def make_gui(*, project: Project | None = None) -> tuple[KleuwGUI, StubMessageBox]:
    """Construct a ``KleuwGUI`` wired to stub widgets for headless tests."""

    root = StubRoot()
    messagebox = StubMessageBox()
    tk_module = build_functional_tk_module()
    ttk_module = build_functional_ttk_module()
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = KleuwGUI(
        root=root,
        tk_module=tk_module,
        ttk_module=ttk_module,
        messagebox_module=messagebox,
        filedialog_module=filedialog,
        enable_tooltips=False,
        project=project,
    )
    return gui, messagebox


def _make_string_var_factory() -> Callable[..., StubStringVar]:
    def _factory(value: str = "", **_: Any) -> StubStringVar:
        return StubStringVar(value)

    return _factory


def _make_boolean_var_factory() -> Callable[..., StubBooleanVar]:
    def _factory(value: bool = False, **_: Any) -> StubBooleanVar:
        return StubBooleanVar(value)

    return _factory
