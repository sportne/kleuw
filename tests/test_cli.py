"""Tests for the Kleuw CLI scaffolding."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from kleuw import cli


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
