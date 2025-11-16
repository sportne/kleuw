"""Tests for the Kleuw CLI scaffolding."""

from __future__ import annotations

import json
from argparse import Namespace
from collections.abc import Sequence
from pathlib import Path

import pytest

from kleuw import cli
from kleuw.io import load_project, save_project
from kleuw.model import FileEntry
from kleuw.project import Project


def parse_args(argv: Sequence[str]):
    """Helper that builds a fresh parser and parses the provided arguments."""

    parser = cli.build_parser()
    return parser.parse_args(argv)


@pytest.mark.parametrize(
    ("argv", "expected_handler"),
    [
        (["init", "project.json"], cli._handle_init),
        (["add-file", "project.json", "src/app.py"], cli._handle_add_file),
        (["list-files", "project.json"], cli._handle_list_files),
        (
            [
                "create-link",
                "project.json",
                "--src",
                "src/app.py:5-10",
                "--dst",
                "tests/test_app.py:1-3",
                "--type",
                "implements",
            ],
            cli._handle_create_link,
        ),
        (["list-links", "project.json"], cli._handle_list_links),
        (["check", "project.json"], cli._handle_check),
        (["recompute", "project.json"], cli._handle_recompute),
        (["validate", "project.json"], cli._handle_validate),
        (["export", "project.json", "--format", "json"], cli._handle_export),
    ],
)
def test_subcommands_register_expected_handlers(argv: list[str], expected_handler):
    args = parse_args(argv)
    assert args.handler is expected_handler


def test_list_links_options_are_wired_correctly():
    args = parse_args(
        [
            "list-links",
            "project.json",
            "--json",
            "--stale-only",
            "--type",
            "implements",
        ]
    )
    assert args.json is True
    assert args.stale_only is True
    assert args.link_type == "implements"


def test_create_link_requires_all_mandatory_options():
    with pytest.raises(SystemExit):
        parse_args(
            [
                "create-link",
                "project.json",
                "--src",
                "src/app.py:5-10",
                "--type",
                "implements",
            ]
        )


def test_main_dispatches_to_selected_handler(monkeypatch):
    called = {}

    def fake_handler(args):
        called["args"] = args
        return 99

    monkeypatch.setattr(cli, "_handle_init", fake_handler)
    # Ensure the patched handler is captured when building the parser within main.
    exit_code = cli.main(["init", "project.json"])

    assert exit_code == 99
    assert called["args"].project == "project.json"


def test_parser_requires_subcommand():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_handle_init_creates_project_file(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"

    exit_code = cli._handle_init(Namespace(project=str(project_path), force=False))

    assert exit_code == 0
    contents = json.loads(project_path.read_text(encoding="utf-8"))
    assert contents == {"version": 1, "files": [], "links": []}


def test_handle_init_requires_force_when_file_exists(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    project_path.write_text("original", encoding="utf-8")

    exit_code = cli._handle_init(Namespace(project=str(project_path), force=False))

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err
    assert project_path.read_text(encoding="utf-8") == "original"


def _create_project(path: Path) -> None:
    save_project(path, Project())


def test_handle_add_file_adds_entry_with_generated_id(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    _create_project(project_path)
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("hello", encoding="utf-8")

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_file),
            file_id=None,
            hash=False,
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    assert project.files == [{"id": "file-1", "path": str(tracked_file)}]


def test_handle_add_file_supports_explicit_id_and_hash(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    _create_project(project_path)
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("hash me", encoding="utf-8")

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_file),
            file_id="custom-id",
            hash=True,
        )
    )

    assert exit_code == 0
    project = load_project(project_path)
    entry = project.find_file_by_id("custom-id")
    assert entry is not None
    assert entry["hash"]["algo"] == "sha256"
    assert len(entry["hash"]["value"]) == 64


def test_handle_add_file_rejects_missing_file(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    _create_project(project_path)
    missing_file = tmp_path / "missing.txt"

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(missing_file),
            file_id=None,
            hash=False,
        )
    )

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


def test_handle_add_file_rejects_duplicate_id(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    project = Project()
    project.add_file(FileEntry(id="existing", path="original.txt"))
    save_project(project_path, project)
    tracked_file = tmp_path / "another.txt"
    tracked_file.write_text("data", encoding="utf-8")

    exit_code = cli._handle_add_file(
        Namespace(
            project=str(project_path),
            path=str(tracked_file),
            file_id="existing",
            hash=False,
        )
    )

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err
