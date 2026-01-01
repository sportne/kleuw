"""GUI tests focused on link-related actions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI
from kleuw.project import Project
from tests._gui_stubs import build_stub_tk_module, build_stub_ttk_module


@pytest.mark.gui()
def test_gui_recompute_hashes_action(tmp_path: Path) -> None:
    """Verify the 'Recompute Hashes' menu action."""
    mock_tk = build_stub_tk_module()
    mock_ttk = build_stub_ttk_module()
    mock_messagebox = MagicMock()
    mock_filedialog = MagicMock()

    src_file = tmp_path / "src.txt"
    src_file.write_text("source\ncontent\n")
    dst_file = tmp_path / "dst.txt"
    dst_file.write_text("destination\ncontent\n")

    project = Project(
        files=[
            {"id": "file-1", "path": str(src_file)},
            {"id": "file-2", "path": str(dst_file)},
        ],
        links=[
            {
                "id": "link-1",
                "type": "references",
                "src": {
                    "file_id": "file-1",
                    "lines": {"start": 1, "end": 1},
                    "src_region_hash": {"algo": "sha256", "value": "stale-hash"},
                },
                "dst": {
                    "file_id": "file-2",
                    "lines": {"start": 1, "end": 1},
                    "dst_region_hash": {"algo": "sha256", "value": "stale-hash"},
                },
            }
        ],
    )
    gui = KleuwGUI(
        root=mock_tk.Tk(),
        project=project,
        tk_module=mock_tk,
        ttk_module=mock_ttk,
        messagebox_module=mock_messagebox,
        filedialog_module=mock_filedialog,
    )

    mock_messagebox.askyesno.return_value = True

    recompute_callback = gui._get_action_callback("Recompute Hashes")
    recompute_callback()

    assert mock_messagebox.askyesno.call_count == 1
    assert (
        "This will recompute hashes" in mock_messagebox.askyesno.call_args[1]["message"]
    )

    assert len(gui._project.links) == 1
    updated_link = gui._project.links[0]
    src_hash = updated_link["src"]["src_region_hash"]["value"]
    dst_hash = updated_link["dst"]["dst_region_hash"]["value"]
    assert src_hash != "stale-hash"
    assert dst_hash != "stale-hash"

    assert "Successfully recomputed" in mock_messagebox.showinfo.call_args[1]["message"]
    assert gui._is_dirty
    assert gui.dirty_var.get() == "● Unsaved changes"


@pytest.mark.gui()
def test_gui_recompute_hashes_action_with_missing_file(tmp_path: Path) -> None:
    """Verify the 'Recompute Hashes' menu action handles a missing file."""
    mock_tk = build_stub_tk_module()
    mock_ttk = build_stub_ttk_module()
    mock_messagebox = MagicMock()
    mock_filedialog = MagicMock()

    src_file = tmp_path / "src.txt"
    src_file.write_text("source\ncontent\n")
    missing_file = tmp_path / "missing.txt"

    project = Project(
        files=[
            {"id": "file-1", "path": str(src_file)},
            {"id": "file-2", "path": str(missing_file)},
        ],
        links=[
            {
                "id": "link-1",
                "type": "references",
                "src": {
                    "file_id": "file-1",
                },
                "dst": {
                    "file_id": "file-2",
                },
            }
        ],
    )
    gui = KleuwGUI(
        root=mock_tk.Tk(),
        project=project,
        tk_module=mock_tk,
        ttk_module=mock_ttk,
        messagebox_module=mock_messagebox,
        filedialog_module=mock_filedialog,
    )

    mock_messagebox.askyesno.return_value = True

    recompute_callback = gui._get_action_callback("Recompute Hashes")
    recompute_callback()

    assert mock_messagebox.askyesno.call_count == 1
    assert "Successfully recomputed" in mock_messagebox.showinfo.call_args[1]["message"]
    assert (
        "No such file or directory" in mock_messagebox.showinfo.call_args[1]["message"]
    )
