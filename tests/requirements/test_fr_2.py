"""Requirement validation tests for FR-2."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from kleuw import cli


def test_fr_2_cli_init_creates_empty_project(tmp_path: Path) -> None:
    """FR-2: the CLI shall create a new empty project file."""

    project_path = tmp_path / "demo_project.json"

    exit_code = cli._handle_init(Namespace(project=str(project_path), force=False))

    assert exit_code == 0, "Expected init to succeed"
    assert project_path.is_file(), "Project file should be created"

    payload = json.loads(project_path.read_text(encoding="utf-8"))
    assert payload == {"version": 1, "files": [], "links": []}
