"""Requirement tests for FR-22 (staleness access via GUI and CLI)."""

from __future__ import annotations

from kleuw import cli
from kleuw.gui import MENU_DEFINITION, TOOLBAR_BUTTONS


def test_fr_22_cli_registers_check_subcommand() -> None:
    """FR-22: The CLI shall expose staleness checks via ``kleuw check``."""

    parser = cli.build_parser()
    args = parser.parse_args(["check", "project.json"])

    assert args.handler is cli._handle_check


def test_fr_22_gui_surfaces_staleness_controls() -> None:
    """FR-22: The GUI shall include staleness actions in menus and toolbar."""

    menu_has_action = any(
        item.label == "Check Staleness"
        for _menu_label, items in MENU_DEFINITION
        for item in items
    )
    toolbar_has_action = any(
        button.label == "Check Staleness" for button in TOOLBAR_BUTTONS
    )

    assert menu_has_action is True
    assert toolbar_has_action is True
