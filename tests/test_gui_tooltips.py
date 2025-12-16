from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest

from kleuw.gui import KleuwGUI
from kleuw.staleness import LinkStalenessResult, TargetStalenessResult

# Mark all tests in this module as GUI tests
pytestmark = pytest.mark.gui


def test_tooltip_shows_for_stale_links_and_hides_for_others(
    mock_tkinter: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that tooltips appear for stale links and hide otherwise."""
    gui = KleuwGUI(tk_module=mock_tkinter, ttk_module=MagicMock())
    tree = gui._links_tree
    assert tree is not None
    tooltip = gui._link_tooltip
    assert tooltip is not None

    # Mock the staleness results
    stale_result = LinkStalenessResult(
        link_id="link-1",
        stale=True,
        reasons=("src changed",),
        src=TargetStalenessResult(True, "src changed", None),
        dst=TargetStalenessResult(False, None, None),
    )
    gui._staleness_results = {"link-1": stale_result}

    # Mock the UI components and event
    mock_event = MagicMock(spec=tk.Event)
    mock_event.y = 10
    monkeypatch.setattr(tooltip, "set_text", MagicMock())
    monkeypatch.setattr(tooltip, "show", MagicMock())
    monkeypatch.setattr(tooltip, "hide", MagicMock())

    # --- Test Case 1: Hover over a stale link ---
    monkeypatch.setattr(tree, "identify_row", lambda y: "link-1")
    gui._show_link_tooltip(mock_event)
    tooltip.set_text.assert_called_once_with("Changed: source")
    tooltip.show.assert_called_once_with(mock_event)
    tooltip.hide.assert_not_called()

    # Reset mocks
    tooltip.set_text.reset_mock()
    tooltip.show.reset_mock()
    tooltip.hide.reset_mock()

    # --- Test Case 2: Hover over a non-stale link ---
    monkeypatch.setattr(tree, "identify_row", lambda y: "link-2")
    gui._show_link_tooltip(mock_event)
    tooltip.set_text.assert_not_called()
    tooltip.show.assert_not_called()
    tooltip.hide.assert_called_once()
    tooltip.hide.reset_mock()

    # --- Test Case 3: Hover over an empty area ---
    monkeypatch.setattr(tree, "identify_row", lambda y: "")
    gui._show_link_tooltip(mock_event)
    tooltip.set_text.assert_not_called()
    tooltip.show.assert_not_called()
    tooltip.hide.assert_called_once()
