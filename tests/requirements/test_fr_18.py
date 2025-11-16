"""Requirement validation tests for FR-18."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from kleuw import cli
from kleuw.hashing import compute_region_hash
from kleuw.io import load_project
from tests.test_cli import _create_project_with_links


def test_fr_18_cli_recompute_overwrites_region_hashes(tmp_path: Path, capsys) -> None:
    """FR-18: `kleuw recompute` refreshes stored region hashes."""

    project_path, src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_recompute(
        Namespace(project=str(project_path), link_ids=None)
    )

    assert exit_code == 0
    project = load_project(project_path)
    entry = project.find_link_by_id("L2")
    assert entry is not None
    expected = compute_region_hash(src_file, start_line=2, end_line=2)
    assert entry["src"]["src_region_hash"]["value"] == expected.value

    capsys.readouterr()  # drain CLI output for cleanliness
