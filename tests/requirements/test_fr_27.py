"""Requirement FR-27: ``kleuw create-link`` parsing and persistence."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.hashing import compute_region_hash
from kleuw.io import load_project
from kleuw.model import LinkType
from tests.requirements._cli_helpers import create_project_with_files


def test_fr_27_create_link_assigns_ids_and_hashes(tmp_path: Path, capsys) -> None:
    project_path, src_file, dst_file = create_project_with_files(tmp_path)

    exit_code = cli._handle_create_link(
        Namespace(
            project=str(project_path),
            src=f"{src_file}:1-2",
            dst=f"{dst_file}:1",
            type=LinkType.IMPLEMENTS.value,
            note="trace",
            tags="req,impl",
        )
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "link-1"
    project = load_project(project_path)
    entry = project.find_link_by_id("link-1")
    assert entry is not None
    assert entry["src"]["file_id"] == "SRC"
    assert entry["dst"]["file_id"] == "DST"
    assert entry["note"] == "trace"
    assert entry["tags"] == ["req", "impl"]

    expected_src_hash = compute_region_hash(src_file, start_line=1, end_line=2)
    expected_dst_hash = compute_region_hash(dst_file, start_line=1, end_line=1)
    assert entry["src"]["src_region_hash"]["value"] == expected_src_hash.value
    assert entry["dst"]["dst_region_hash"]["value"] == expected_dst_hash.value
