"""Requirement FR-24: ``kleuw init`` project creation behavior."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from kleuw import cli


def test_fr_24_init_creates_new_project(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"

    exit_code = cli._handle_init(Namespace(project=str(project_path), force=False))

    assert exit_code == 0
    payload = json.loads(project_path.read_text(encoding="utf-8"))
    assert payload == {"version": 1, "files": [], "links": []}


def test_fr_24_init_overwrites_when_forced(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    project_path.write_text("original", encoding="utf-8")

    exit_code = cli._handle_init(Namespace(project=str(project_path), force=True))

    assert exit_code == 0
    payload = json.loads(project_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
