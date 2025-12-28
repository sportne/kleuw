"""Tests for file loading behavior in the Kleuw GUI viewers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI
from kleuw.hashing import compute_region_hash
from kleuw.model import LineSpan, Link, LinkType, Target
from kleuw.project import Project
from tests._gui_stubs import (
    StubMessageBox,
    StubRoot,
    StubStringVar,
    _create_fake_menu,
)


class _BaseWidget:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._bindings: dict[str, Callable[..., Any]] = {}

    def pack(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - layout helper
        return None

    def grid(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - layout helper
        return None

    def bind(self, sequence: str, callback: Callable[..., Any]) -> None:
        self._bindings[sequence] = callback

    def destroy(self) -> None:  # pragma: no cover - tooltip helper
        return None


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
        self.tags: dict[str, dict[str, Any]] = {}
        self.tag_ranges: dict[str, list[tuple[str, str]]] = {}

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

    def tag_configure(self, name: str, **kwargs: Any) -> None:
        self.tags[name] = kwargs

    def tag_remove(self, name: str, *_args: Any, **_kwargs: Any) -> None:
        self.tag_ranges[name] = []

    def tag_add(self, name: str, start: str, end: str) -> None:
        self.tag_ranges.setdefault(name, []).append((start, end))

    def index(self, _spec: str) -> str:
        return "1.0"


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
    instances: list[_FakeButton] = []

    def __init__(
        self, *_args: Any, command: Callable[..., Any] | None = None, **_kwargs: Any
    ) -> None:
        super().__init__()
        self.command = command
        self.state = "normal"
        self.__class__.instances.append(self)

    def configure(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]

    config = configure


class _FakeEntry(_BaseWidget):
    def __init__(
        self, *_args: Any, textvariable: StubStringVar | None = None, **_kwargs: Any
    ) -> None:
        super().__init__()
        self.textvariable = textvariable
        self.value = textvariable.get() if textvariable is not None else ""

    def get(self) -> str:
        return self.value

    def insert(self, index: Any, value: str) -> None:  # pragma: no cover - unused
        self.value = value

    def delete(
        self, start: Any, end: Any | None = None
    ) -> None:  # pragma: no cover - unused
        self.value = ""

    def focus_set(self) -> None:  # pragma: no cover - noop
        return None

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
        self.items: dict[str, tuple[str, ...]] = {}
        self.order: list[str] = []
        self._selection: tuple[str, ...] = ()
        self.tag_styles: dict[str, dict[str, Any]] = {}
        self.item_tags: dict[str, tuple[str, ...]] = {}

    def heading(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def column(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def configure(self, **kwargs: Any) -> None:
        if "yscrollcommand" in kwargs:
            self.yscrollcommand = kwargs["yscrollcommand"]

    config = configure

    def insert(
        self,
        _parent: Any,
        _index: Any,
        *,
        iid: str | None = None,
        values: tuple[str, ...],
        tags: Sequence[str] | None = None,
    ) -> str:
        identifier = iid if iid is not None else f"row-{len(self.rows)}"
        self.rows.append(values)
        self.items[identifier] = values
        self.order.append(identifier)
        self.item_tags[identifier] = tuple(tags) if tags else ()
        return identifier

    def yview(self, *args: Any) -> None:
        self.last_yview = args

    def selection(self) -> tuple[str, ...]:
        return self._selection

    def selection_set(self, *items: Any) -> None:
        flattened: list[str] = []
        for entry in items:
            if isinstance(entry, (list, tuple)):
                flattened.extend(str(part) for part in entry)
            else:
                flattened.append(str(entry))
        self._selection = tuple(flattened)

    def get_children(self) -> tuple[str, ...]:
        return tuple(self.order)

    def delete(self, item: str) -> None:
        if item in self.items:
            del self.items[item]
        if item in self.item_tags:
            del self.item_tags[item]
        self.order = [existing for existing in self.order if existing != item]

    def tag_configure(self, name: str, **kwargs: Any) -> None:
        self.tag_styles[name] = kwargs


class _FakeSeparator(_BaseWidget):
    pass


class _FakeStyle:
    def configure(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - trivial
        return None

    def map(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - trivial
        return None


class _FakeToplevel(_BaseWidget):
    def title(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
        return None

    def wm_overrideredirect(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - tooltip helper
        return None

    def wm_geometry(
        self, *_args: Any, **_kwargs: Any
    ) -> None:  # pragma: no cover - tooltip helper
        return None

    def transient(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
        return None

    def grab_set(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
        return None


@pytest.fixture()
def functional_tk_module() -> SimpleNamespace:
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
    module.StringVar = lambda value="", **_: StubStringVar(value)  # type: ignore[assignment]
    return module


@pytest.fixture()
def functional_ttk_module() -> SimpleNamespace:
    module = SimpleNamespace()
    module.Frame = _FakeFrame
    module.Button = _FakeButton
    module.Button.instances = []
    module.Label = _FakeLabel
    module.PanedWindow = _FakePanedWindow
    module.Scrollbar = _FakeScrollbar
    module.Combobox = _FakeCombobox
    module.Treeview = _FakeTreeview
    module.Separator = _FakeSeparator
    module.Entry = _FakeEntry
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
    *,
    project: Project | None = None,
) -> KleuwGUI:
    return KleuwGUI(
        root=stub_root,
        tk_module=tk_module,
        ttk_module=ttk_module,
        messagebox_module=messagebox,
        enable_tooltips=False,
        filedialog_module=filedialog_module,
        project=project,
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


def test_selection_summary_updates_with_line_selection(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left_file = tmp_path / "left.txt"
    left_file.write_text("one\ntwo\nthree\n")
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )
    assert gui._left_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left_file))
    gui._set_viewer_selection(gui._left_viewer, 2, 3)
    assert gui.selection_var.get().startswith("Selections: Left L2–L3")


def test_swap_viewers_exchanges_files_and_selections(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("alpha\nbeta")
    right_file.write_text("one\ntwo\nthree")
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left_file))
    gui._load_file_into_viewer(gui._right_viewer, str(right_file))
    gui._set_viewer_selection(gui._left_viewer, 1, 2)
    gui._set_viewer_selection(gui._right_viewer, 3, 3)

    gui._swap_viewer_files()

    assert gui._left_viewer.file_path == str(right_file)
    assert gui._right_viewer.file_path == str(left_file)
    assert gui.selection_var.get().startswith("Selections: Left L3")


def test_create_link_button_enables_after_requirements_met(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("alpha")
    right_file.write_text("bravo")
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
    )
    assert gui._create_link_button is not None
    assert gui._create_link_button.state == "disabled"
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left_file))
    gui._load_file_into_viewer(gui._right_viewer, str(right_file))
    gui._update_create_button_state()
    assert gui._create_link_button.state == "disabled"
    gui.relationship_var.set(LinkType.IMPLEMENTS.value)
    gui._update_create_button_state()
    assert gui._create_link_button.state == "normal"


def test_create_link_uses_project_and_hashes(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("left-one\nleft-two")
    right_file.write_text("right-one")
    project = Project(
        files=[
            {"id": "src", "path": str(left_file)},
            {"id": "dst", "path": str(right_file)},
        ]
    )
    filedialog = SimpleNamespace(askopenfilenames=lambda **_: ())
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        filedialog,
        project=project,
    )
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left_file))
    gui._load_file_into_viewer(gui._right_viewer, str(right_file))
    gui._set_viewer_selection(gui._left_viewer, 1, 1)
    gui.relationship_var.set(LinkType.IMPLEMENTS.value)
    gui._update_create_button_state()

    gui._create_link()

    assert len(project.links) == 1
    entry = project.links[0]
    assert entry["type"] == LinkType.IMPLEMENTS.value
    assert entry["src"]["file_id"] == "src"
    assert entry["src"]["lines"]["start"] == 1
    assert entry["src"]["lines"]["end"] == 1
    assert "src_region_hash" in entry["src"]
    assert entry["dst"]["file_id"] == "dst"
    assert "lines" not in entry["dst"]


def test_create_link_requires_files_loaded(
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    gui._create_link()
    assert "Load files" in stub_messagebox.info_calls[-1][1]


def test_create_link_requires_relationship_type(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("one")
    right.write_text("two")
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left))
    gui._load_file_into_viewer(gui._right_viewer, str(right))
    gui._create_link()
    assert "relationship type" in stub_messagebox.info_calls[-1][1]


def test_create_link_rejects_unknown_relationship(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("one")
    right.write_text("two")
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    gui._load_file_into_viewer(gui._left_viewer, str(left))
    gui._load_file_into_viewer(gui._right_viewer, str(right))
    gui.relationship_var.set("invalid")
    gui._create_link()
    assert "Unknown relationship type" in stub_messagebox.error_calls[-1][1]


def _project_with_links(tmp_path: Path) -> tuple[Project, Path, Path]:
    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("one\ntwo\nthree")
    right_file.write_text("alpha\nbeta")
    project = Project(
        files=[
            {"id": "src", "path": str(left_file)},
            {"id": "dst", "path": str(right_file)},
        ],
        links=[
            {
                "id": "L1",
                "type": LinkType.IMPLEMENTS.value,
                "src": {"file_id": "src", "lines": {"start": 2, "end": 3}},
                "dst": {"file_id": "dst", "lines": {"start": 1}},
            }
        ],
    )
    return project, left_file, right_file


def _project_with_hashed_link(tmp_path: Path) -> tuple[Project, Path, Path]:
    left_file = tmp_path / "left.txt"
    right_file = tmp_path / "right.txt"
    left_file.write_text("left-one\nleft-two\n")
    right_file.write_text("right-one\nright-two\n")
    project = Project(
        files=[
            {"id": "src", "path": str(left_file)},
            {"id": "dst", "path": str(right_file)},
        ],
        links=[],
    )
    project.add_link(
        Link(
            id="L1",
            type=LinkType.IMPLEMENTS,
            src=Target(
                file_id="src",
                lines=LineSpan(start=1, end=1),
                region_hash=compute_region_hash(
                    str(left_file), start_line=1, end_line=1
                ),
            ),
            dst=Target(
                file_id="dst",
                lines=LineSpan(start=1, end=1),
                region_hash=compute_region_hash(
                    str(right_file), start_line=1, end_line=1
                ),
            ),
        )
    )
    return project, left_file, right_file


def test_links_panel_populates_with_project_links(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, left_file, right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    assert gui._links_tree is not None
    expected = (
        "L1",
        LinkType.IMPLEMENTS.value,
        f"{left_file} L2–L3",
        f"{right_file} L1",
        "Unknown",
        "",
        "",
    )
    assert gui._links_tree.items["L1"] == expected  # type: ignore[index]


def test_links_panel_shows_tags_and_note(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, left_file, right_file = _project_with_links(tmp_path)
    link = project.find_link_by_id("L1")
    assert link is not None
    link["tags"] = ["alpha", "beta"]
    link["note"] = "details"
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    assert gui._links_tree is not None
    values = gui._links_tree.items["L1"]  # type: ignore[index]
    assert values[5] == "alpha, beta"
    assert values[6] == "Yes"


def test_navigate_to_link_loads_files_and_selections(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, left_file, right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    gui._navigate_to_link_id("L1")
    assert gui.relationship_var.get() == LinkType.IMPLEMENTS.value
    assert gui._left_viewer is not None
    assert gui._right_viewer is not None
    assert gui._left_viewer.file_path == str(left_file)
    assert gui._left_viewer.selection_start == 2
    assert gui._left_viewer.selection_end == 3
    assert gui._right_viewer.file_path == str(right_file)
    assert gui._right_viewer.selection_start == 1


def test_check_staleness_updates_summary_and_rows(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, _left_file, _right_file = _project_with_hashed_link(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    button_start = len(functional_ttk_module.Button.instances)
    gui._run_staleness_check()
    dialog_buttons = functional_ttk_module.Button.instances[button_start:]

    assert gui._links_tree is not None
    assert gui._links_tree.items["L1"][4] == "No"  # type: ignore[index]
    assert gui.staleness_var.get() == "Staleness: 0 stale of 1"
    assert dialog_buttons
    assert dialog_buttons[0].state == "disabled"  # type: ignore[index]
    assert gui._show_all_links_button is not None
    assert gui._show_all_links_button.state == "disabled"  # type: ignore[union-attr]


def test_view_stale_links_filters_tree(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, left_file, right_file = _project_with_hashed_link(tmp_path)
    project.add_link(
        Link(
            id="L2",
            type=LinkType.DEPENDS_ON,
            src=Target(
                file_id="src",
                lines=LineSpan(start=2, end=2),
                region_hash=compute_region_hash(
                    str(left_file), start_line=2, end_line=2
                ),
            ),
            dst=Target(
                file_id="dst",
                lines=LineSpan(start=2, end=2),
                region_hash=compute_region_hash(
                    str(right_file), start_line=2, end_line=2
                ),
            ),
        )
    )
    left_file.write_text("left-one\nchanged-two\n")
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    button_start = len(functional_ttk_module.Button.instances)
    gui._run_staleness_check()
    dialog_buttons = functional_ttk_module.Button.instances[button_start:]
    assert dialog_buttons
    view_button = dialog_buttons[0]
    assert view_button.command is not None
    view_button.command()

    assert gui._links_tree is not None
    assert gui._links_tree.items["L2"][4] == "Yes"  # type: ignore[index]
    assert gui._links_tree.item_tags["L2"] == ("stale",)  # type: ignore[index]

    assert gui._links_tree.get_children() == ("L2",)
    assert gui.staleness_var.get().endswith("(filtered)")
    assert gui._show_all_links_button is not None
    assert gui._show_all_links_button.state == "normal"  # type: ignore[union-attr]

    gui._clear_links_filter()
    assert set(gui._links_tree.get_children()) == {"L1", "L2"}


def test_check_staleness_handles_invalid_links(
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project = Project(links=[{"id": "broken", "type": LinkType.IMPLEMENTS.value}])
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )

    gui._run_staleness_check()

    assert stub_messagebox.error_calls
    assert "Invalid" in stub_messagebox.error_calls[-1][1]


def test_delete_selected_link_updates_project(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, _left_file, _right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    assert gui._links_tree is not None
    gui._links_tree.selection_set("L1")  # type: ignore[union-attr]
    gui._delete_selected_links()
    assert project.links == []


def test_apply_link_edit_updates_metadata(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, _left_file, _right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    gui._apply_link_edit(
        "L1",
        type_value=LinkType.DEFINES.value,
        tags_text="foo, bar",
        note_text=" updated ",
    )
    entry = project.find_link_by_id("L1")
    assert entry is not None
    assert entry["type"] == LinkType.DEFINES.value
    assert entry["tags"] == ["foo", "bar"]
    assert entry["note"] == "updated"


def test_apply_link_edit_rejects_unknown_type(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    project, _left_file, _right_file = _project_with_links(tmp_path)
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
        project=project,
    )
    gui._apply_link_edit("L1", type_value="unknown", tags_text="", note_text="")
    assert "Unknown relationship type" in stub_messagebox.error_calls[-1][1]


def test_load_target_into_viewer_requires_known_file(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    assert gui._left_viewer is not None
    with pytest.raises(ValueError, match="unknown file"):
        gui._load_target_into_viewer(
            gui._left_viewer, {"file_id": "missing"}, label="Left"
        )


def test_compute_target_hash_reports_missing_file(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    missing = tmp_path / "missing.txt"
    with pytest.raises(ValueError, match="does not exist"):
        gui._compute_target_hash(str(missing), lines=None, label="source")


def test_compute_target_hash_reports_invalid_range(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("alpha\n")
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    with pytest.raises(ValueError, match="Invalid line range"):
        gui._compute_target_hash(str(source), lines=LineSpan(start=5), label="source")


def test_compute_target_hash_reports_unicode_error(
    tmp_path: Path,
    functional_tk_module: SimpleNamespace,
    functional_ttk_module: SimpleNamespace,
    stub_messagebox: StubMessageBox,
) -> None:
    source = tmp_path / "binary.bin"
    source.write_bytes(b"\xff\xfe")
    gui = _make_gui(
        StubRoot(),
        functional_tk_module,
        functional_ttk_module,
        stub_messagebox,
        SimpleNamespace(askopenfilenames=lambda **_: ()),
    )
    with pytest.raises(ValueError, match="not valid UTF-8"):
        gui._compute_target_hash(str(source), lines=None, label="destination")
