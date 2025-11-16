"""Requirement FR-28: ``kleuw check`` diagnostics and staleness pipeline."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from kleuw import cli
from tests.requirements._cli_helpers import create_project_with_links


def test_fr_28_check_reports_stale_status_and_exit_code(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=None, json=False)
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "STALE" in output and "OK" in output


def test_fr_28_check_supports_json_and_link_filters(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=["L1"], json=True)
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 1
    assert payload["stale"] == 0
    assert payload["results"][0]["id"] == "L1"


def test_fr_28_list_links_stale_only_uses_same_pipeline(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_list_links(
        Namespace(project=str(project_path), json=True, stale_only=True, link_type=None)
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [link["id"] for link in payload["links"]] == ["L2"]
