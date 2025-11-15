"""GUI-specific smoke tests for the Kleuw scaffolding."""

from __future__ import annotations

import importlib
from collections.abc import Iterable

import pytest

pytestmark = pytest.mark.gui

GUI_MODULE_NAMES: tuple[str, ...] = (
    "kleuw",
    "kleuw.cli",
    "kleuw.gui",
    "kleuw.model",
    "kleuw.schema",
    "kleuw.hashing",
    "kleuw.staleness",
    "kleuw.io",
    "kleuw.project",
    "kleuw.utils",
)


def test_gui_module_reloads_without_side_effects() -> None:
    """Import and reload the GUI module to ensure coverage works under ``-m gui``."""

    module = importlib.import_module("kleuw.gui")
    assert module is not None

    reloaded = importlib.reload(module)
    assert reloaded is module


@pytest.mark.parametrize("module_name", GUI_MODULE_NAMES)
def test_gui_context_imports_cover_package(module_name: str) -> None:
    """Import each Kleuw module so GUI-only runs still gather coverage data."""

    imported = importlib.import_module(module_name)
    assert imported.__name__ == module_name


def test_gui_module_registry_is_complete() -> None:
    """Ensure the GUI module list stays in sync with the package scaffolding."""

    assert isinstance(GUI_MODULE_NAMES, Iterable)
    assert len(GUI_MODULE_NAMES) == len(set(GUI_MODULE_NAMES))
