"""Validation tests for FR-11 (relationship type selection)."""

from __future__ import annotations

from kleuw.model import LinkType
from tests.requirements._gui_helpers import make_gui


def test_fr_11_relationship_types_match_enumeration() -> None:
    """FR-11: GUI combobox exposes only the enumerated relationship types."""

    gui, _ = make_gui()
    available = gui._relationship_values
    expected = tuple(link_type.value for link_type in LinkType)

    assert available == expected
    assert gui.relationship_var.get() == ""

    gui.relationship_var.set(available[0])
    gui._update_create_button_state()
    assert gui.relationship_var.get() == available[0]
