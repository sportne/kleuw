"""Tests for project I/O behavior in the Kleuw GUI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from kleuw.gui import KleuwGUI
from kleuw.project import Project
from tests._gui_stubs import StubMessageBox, StubRoot, build_stub_tk_module, build_stub_ttk_module


@pytest.fixture
def gui_stubs() -> SimpleNamespace:
    return SimpleNamespace(tk=build_stub_tk_module(), ttk=build_stub_ttk_module())


def _make_gui(
    gui_stubs: SimpleNamespace,
    filedialog_module: SimpleNamespace,
    *,
    project: Project | None = None,
) -> KleuwGUI:
    return KleuwGUI(
        root=StubRoot(),
        tk_module=gui_stubs.tk,
        ttk_module=gui_stubs.ttk,
        messagebox_module=StubMessageBox(),
        enable_tooltips=False,
        filedialog_module=filedialog_module,
        project=project,
    )


def test_new_project_clears_state(gui_stubs: SimpleNamespace) -> None:
    filedialog = SimpleNamespace()
    project = Project(files=[{"id": "f1", "path": "/a"}], links=[{"id": "l1"}])
    gui = _make_gui(gui_stubs, filedialog, project=project)
    gui.dirty_var.set("● Unsaved changes")
    gui._messagebox.askyesno_response = True

    gui._new_project()

    assert not gui._project.files
    assert not gui._project.links
    assert gui._project_path is None
    assert "New Project" in gui.project_path_var.get()
    assert "Clean" in gui.dirty_var.get()


def test_open_project_loads_data(tmp_path: Path, gui_stubs: SimpleNamespace) -> None:
    proj_path = tmp_path / "project.json"
    proj_path.write_text('{"version": 1, "files": [{"id": "f1", "path": "a.txt"}], "links": []}')
    filedialog = SimpleNamespace(askopenfilename=lambda **_: str(proj_path))
    gui = _make_gui(gui_stubs, filedialog)

    gui._open_project()

    assert len(gui._project.files) == 1
    assert gui._project.files[0]["path"] == "a.txt"
    assert gui._project_path == str(proj_path)


def test_save_project_writes_to_path(
    tmp_path: Path, gui_stubs: SimpleNamespace
) -> None:
    proj_path = tmp_path / "project.json"
    filedialog = SimpleNamespace(asksaveasfilename=lambda **_: str(proj_path))
    project = Project(files=[{"id": "f1", "path": "a.txt"}])
    gui = _make_gui(gui_stubs, filedialog, project=project)
    gui._project_path = str(proj_path)

    gui._save_project()

    assert "Clean" in gui.dirty_var.get()
    assert proj_path.read_text() == '{\n  "files": [\n    {\n      "id": "f1",\n      "path": "a.txt"\n    }\n  ],\n  "links": [],\n  "version": 1\n}\n'


def test_save_project_as_prompts_for_path(
    tmp_path: Path, gui_stubs: SimpleNamespace
) -> None:
    proj_path = tmp_path / "new-project.json"
    filedialog = SimpleNamespace(asksaveasfilename=lambda **_: str(proj_path))
    gui = _make_gui(gui_stubs, filedialog)

    gui._save_project_as()

    assert gui._project_path == str(proj_path)
    assert proj_path.exists()
