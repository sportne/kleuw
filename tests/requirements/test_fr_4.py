"""Requirement validation tests for FR-4."""

from __future__ import annotations

from kleuw.gui import KleuwGUI
from tests._gui_stubs import (
    StubMessageBox,
    StubRoot,
    build_stub_tk_module,
    build_stub_ttk_module,
)


class LinkTreeStub:
    """Minimal stub mimicking the Treeview API used by ``KleuwGUI``."""

    def __init__(self, selected: tuple[str, ...] = ()) -> None:
        self._selected = selected
        self.children: list[str] = ["existing-item"]
        self.deleted: list[str] = []
        self.inserted: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
        self.selection_updates: list[str] = []

    def selection(self) -> tuple[str, ...]:
        return self._selected

    def get_children(self) -> list[str]:
        return list(self.children)

    def delete(self, item: str) -> None:
        self.deleted.append(item)

    def insert(
        self,
        _parent: str,
        _index: str,
        *,
        iid: str,
        values: tuple[str, ...],
        tags: tuple[str, ...],
    ) -> None:  # pragma: no cover - exercised indirectly
        self.inserted.append((iid, values, tags))

    def selection_set(self, iid: str) -> None:  # pragma: no cover - defensive
        self.selection_updates.append(iid)


def _build_gui() -> KleuwGUI:
    return KleuwGUI(
        root=StubRoot(),
        tk_module=build_stub_tk_module(),
        ttk_module=build_stub_ttk_module(),
        messagebox_module=StubMessageBox(),
        enable_tooltips=False,
    )


def test_fr_4_dirty_indicator_tracks_unsaved_changes() -> None:
    """FR-4: modifying links toggles the dirty indicator."""

    gui = _build_gui()
    assert gui.dirty_var.get() == "● Clean"

    gui._project.links.append({"id": "link-1"})
    gui._links_tree = LinkTreeStub(selected=("link-1",))

    gui._delete_selected_links()

    assert gui.dirty_var.get() == "● Unsaved changes"
