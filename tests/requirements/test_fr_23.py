"""Requirement tests for FR-23 (link-level staleness selection)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.hashing import compute_region_hash
from kleuw.io import save_project
from kleuw.model import FileEntry, LineSpan, Link, LinkType, Target
from kleuw.project import Project


def _project_with_two_links(tmp_path: Path) -> Path:
    project_path = tmp_path / "project.json"
    src_file = tmp_path / "src.txt"
    dst_file = tmp_path / "dst.txt"
    src_file.write_text("alpha\nbeta\n", encoding="utf-8")
    dst_file.write_text("omega\n", encoding="utf-8")

    project = Project()
    project.add_file(FileEntry(id="SRC", path=str(src_file)))
    project.add_file(FileEntry(id="DST", path=str(dst_file)))

    first_line = compute_region_hash(src_file, start_line=1, end_line=1)
    second_line = compute_region_hash(src_file, start_line=2, end_line=2)
    dst_line = compute_region_hash(dst_file, start_line=1, end_line=1)

    project.add_link(
        Link(
            id="L1",
            type=LinkType.IMPLEMENTS,
            src=Target(
                file_id="SRC",
                lines=LineSpan(start=1, end=1),
                region_hash=first_line,
            ),
            dst=Target(
                file_id="DST",
                lines=LineSpan(start=1, end=1),
                region_hash=dst_line,
            ),
        )
    )
    project.add_link(
        Link(
            id="L2",
            type=LinkType.IMPLEMENTS,
            src=Target(
                file_id="SRC",
                lines=LineSpan(start=2, end=2),
                region_hash=second_line,
            ),
            dst=Target(
                file_id="DST",
                lines=LineSpan(start=1, end=1),
                region_hash=dst_line,
            ),
        )
    )

    save_project(project_path, project)
    src_file.write_text("alpha\nchanged\n", encoding="utf-8")
    return project_path


def test_fr_23_can_check_all_links(tmp_path: Path, capsys) -> None:
    """FR-23: Users may compute staleness for all links in a project."""

    project_path = _project_with_two_links(tmp_path)
    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=None, json=True)
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["total"] == 2
    assert payload["stale"] == 1
    assert {result["id"] for result in payload["results"]} == {"L1", "L2"}


def test_fr_23_can_check_individual_links(tmp_path: Path, capsys) -> None:
    """FR-23: Users may compute staleness for a specific subset of links."""

    project_path = _project_with_two_links(tmp_path)
    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=["L1"], json=True)
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["total"] == 1
    assert payload["stale"] == 0
    assert payload["results"][0]["id"] == "L1"
