"""Requirement FR-29: ``kleuw recompute`` updates region hashes."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.hashing import compute_region_hash
from kleuw.io import load_project
from tests.requirements._cli_helpers import create_project_with_links


def test_fr_29_recompute_refreshes_hashes(tmp_path: Path, capsys) -> None:
    project_path, src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_recompute(
        Namespace(project=str(project_path), link_ids=None)
    )

    assert exit_code == 0
    project = load_project(project_path)
    link_entry = project.find_link_by_id("L2")
    assert link_entry is not None
    expected_hash = compute_region_hash(src_file, start_line=2, end_line=2)
    assert link_entry["src"]["src_region_hash"]["value"] == expected_hash.value

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=None, json=False)
    )
    assert exit_code == 0
    capsys.readouterr()
