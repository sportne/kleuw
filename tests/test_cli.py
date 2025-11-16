"""Tests for the Kleuw CLI scaffolding."""

from __future__ import annotations

import csv
import json
from argparse import Namespace
from collections.abc import Sequence
from io import StringIO
from pathlib import Path

import pytest

from kleuw import cli
from kleuw.hashing import compute_region_hash
from kleuw.io import load_project, save_project
from kleuw.model import FileEntry, LinkType
from kleuw.project import Project
from tests.requirements._cli_helpers import (
    create_project,
    create_project_with_files,
    create_project_with_links,
)


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
    create_project(path)


def _create_project_with_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    return create_project_with_files(tmp_path)


def _create_project_with_links(tmp_path: Path) -> tuple[Path, Path, Path]:
    return create_project_with_links(tmp_path)


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


def test_handle_list_files_supports_table_and_json(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("tracked", encoding="utf-8")
    project = Project()
    project.add_file(
        FileEntry(id="file-1", path=str(tracked_file), lang="py", note="main")
    )
    save_project(project_path, project)

    exit_code = cli._handle_list_files(Namespace(project=str(project_path), json=False))
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ID" in output
    assert "file-1" in output
    assert "py" in output

    exit_code = cli._handle_list_files(Namespace(project=str(project_path), json=True))
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"][0]["id"] == "file-1"


def test_handle_list_links_prints_table(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_list_links(
        Namespace(
            project=str(project_path), json=False, stale_only=False, link_type=None
        )
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ID" in output
    assert "L1" in output and "L2" in output
    assert "file-1:1" in output
    assert "file-1:2" in output
    assert "yes" in output  # stale row is shown


def test_handle_list_links_supports_json_and_filters(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_list_links(
        Namespace(
            project=str(project_path),
            json=True,
            stale_only=True,
            link_type=LinkType.TESTS.value,
        )
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [link["id"] for link in payload["links"]] == ["L2"]


def test_handle_create_link_adds_entry_and_prints_id(tmp_path: Path, capsys) -> None:
    project_path, src_file, dst_file = _create_project_with_files(tmp_path)

    exit_code = cli._handle_create_link(
        Namespace(
            project=str(project_path),
            src=f"{src_file}:1-2",
            dst=f"{dst_file}:1",
            type=LinkType.IMPLEMENTS.value,
            note="trace note",
            tags="reqs,tests",
        )
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    assert output == "link-1"

    project = load_project(project_path)
    link_entry = project.find_link_by_id("link-1")
    assert link_entry is not None
    assert link_entry["src"]["file_id"] == "SRC"
    assert link_entry["dst"]["file_id"] == "DST"
    assert link_entry["note"] == "trace note"
    assert link_entry["tags"] == ["reqs", "tests"]

    expected_src_hash = compute_region_hash(src_file, start_line=1, end_line=2)
    expected_dst_hash = compute_region_hash(dst_file, start_line=1, end_line=1)
    assert link_entry["src"]["src_region_hash"]["value"] == expected_src_hash.value
    assert link_entry["dst"]["dst_region_hash"]["value"] == expected_dst_hash.value


def test_handle_create_link_rejects_unknown_type(tmp_path: Path, capsys) -> None:
    project_path, src_file, dst_file = _create_project_with_files(tmp_path)

    exit_code = cli._handle_create_link(
        Namespace(
            project=str(project_path),
            src=str(src_file),
            dst=str(dst_file),
            type="unknown",
            note=None,
            tags=None,
        )
    )

    assert exit_code == 1
    assert "Unknown link type" in capsys.readouterr().err


def test_handle_create_link_reports_missing_source(tmp_path: Path, capsys) -> None:
    project_path, _src_file, dst_file = _create_project_with_files(tmp_path)
    missing_source = tmp_path / "missing.txt"

    exit_code = cli._handle_create_link(
        Namespace(
            project=str(project_path),
            src=str(missing_source),
            dst=f"{dst_file}:1",
            type=LinkType.IMPLEMENTS.value,
            note=None,
            tags=None,
        )
    )

    assert exit_code == 1
    assert "Source file" in capsys.readouterr().err


def test_handle_check_reports_results_and_exit_codes(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=None, json=False)
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "L1" in output and "L2" in output
    assert "STALE" in output and "OK" in output


def test_handle_check_supports_json_and_link_filter(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=["L1"], json=True)
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 1
    assert payload["stale"] == 0
    assert payload["results"][0]["id"] == "L1"


def test_handle_check_errors_on_unknown_link(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=["missing"], json=False)
    )

    assert exit_code == 1
    assert "Unknown link id" in capsys.readouterr().err


def test_handle_recompute_updates_hashes(tmp_path: Path, capsys) -> None:
    project_path, src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_recompute(
        Namespace(project=str(project_path), link_ids=None)
    )

    assert exit_code == 0
    project = load_project(project_path)
    link_entry = project.find_link_by_id("L2")
    assert link_entry is not None
    expected_hash = compute_region_hash(src_file, start_line=2, end_line=2)
    assert link_entry["src"]["src_region_hash"]["value"] == expected_hash.value

    # Freshness check should now pass
    exit_code = cli._handle_check(
        Namespace(project=str(project_path), link_ids=None, json=False)
    )
    assert exit_code == 0
    capsys.readouterr()  # Drain output


def test_handle_validate_reports_success(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    _create_project(project_path)

    exit_code = cli._handle_validate(Namespace(project=str(project_path)))

    assert exit_code == 0
    assert "Project is valid" in capsys.readouterr().out


def test_handle_validate_reports_schema_errors(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "project.json"
    project_path.write_text("{}", encoding="utf-8")

    exit_code = cli._handle_validate(Namespace(project=str(project_path)))

    assert exit_code == 1
    error_output = capsys.readouterr().err
    assert "Project validation failed" in error_output
    assert "Missing required field 'version'" in error_output


def test_handle_export_supports_json_and_stale_filter(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="json", stale=False)
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["files"] == 2
    assert payload["summary"]["links"] == 2
    assert payload["summary"]["stale_links"] == 1
    assert {link["id"] for link in payload["links"]} == {"L1", "L2"}

    exit_code = cli._handle_export(
        Namespace(project=str(project_path), format="json", stale=True)
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["exported_links"] == 1
    assert [link["id"] for link in payload["links"]] == ["L2"]


def test_handle_export_supports_csv_and_text(tmp_path: Path, capsys) -> None:
    project_path, _src_file, _dst_file = _create_project_with_links(tmp_path)

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
