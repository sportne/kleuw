"""Requirement FR-31: ``kleuw export`` formats and stale filter."""

from __future__ import annotations

import csv
import json
from argparse import Namespace
from io import StringIO
from pathlib import Path

from kleuw import cli
from tests.requirements._cli_helpers import create_project_with_links


def test_fr_31_export_json_supports_stale_filter(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="json", stale=False)
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["files"] == 2
    assert payload["summary"]["links"] == 2
    assert payload["summary"]["stale_links"] == 1

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="json", stale=True)
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["exported_links"] == 1
    assert [link["id"] for link in payload["links"]] == ["L2"]


def test_fr_31_export_csv_and_text_formats(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = create_project_with_links(tmp_path)

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="csv", stale=False)
    )
    assert exit_code == 0
    rows = list(csv.DictReader(StringIO(capsys.readouterr().out)))
    assert any(row["section"] == "file" for row in rows)
    assert any(row["section"] == "link" for row in rows)

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="txt", stale=True)
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Files:" in output and "Links:" in output
    assert "Exported links: 1 (stale only)" in output
