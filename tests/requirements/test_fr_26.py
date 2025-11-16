"""Requirement FR-26: listing commands output formats."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.io import save_project
from kleuw.model import FileEntry
from kleuw.project import Project
from tests.requirements._cli_helpers import create_project_with_links


def test_fr_26_list_files_supports_table_and_json(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("tracked", encoding="utf-8")
    project = Project()
    project.add_file(
        FileEntry(id="file-1", path=str(tracked_file), lang="py", note="main")
    )
    save_project(project_path, project)

    exit_code = cli._handle_list_files(Namespace(project=str(project_path), json=False))
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ID" in output and "file-1" in output and "py" in output

    exit_code = cli._handle_list_files(Namespace(project=str(project_path), json=True))
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"][0]["id"] == "file-1"


def test_fr_26_list_links_supports_table_and_json(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_list_links(
        Namespace(
            project=str(project_path), json=False, stale_only=False, link_type=None
        )
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ID" in output and "file-1:1" in output

    exit_code = cli._handle_list_links(
        Namespace(
            project=str(project_path), json=True, stale_only=False, link_type=None
        )
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert {link["id"] for link in payload["links"]} == {"L1", "L2"}
