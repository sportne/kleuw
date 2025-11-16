"""Requirement FR-30: ``kleuw validate`` schema enforcement."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from kleuw import cli
from tests.requirements._cli_helpers import create_project


def test_fr_30_validate_reports_success(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    create_project(project_path)

    exit_code = cli._handle_validate(Namespace(project=str(project_path)))

    assert exit_code == 0
    assert "Project is valid" in capsys.readouterr().out


def test_fr_30_validate_reports_schema_errors(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    project_path.write_text("{}", encoding="utf-8")

    exit_code = cli._handle_validate(Namespace(project=str(project_path)))

    assert exit_code == 1
    error_output = capsys.readouterr().err
    assert "Project validation failed" in error_output
    assert "Missing required field 'version'" in error_output
