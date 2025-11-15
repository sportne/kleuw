"""Basic import smoke tests for the Kleuw package scaffolding."""

from __future__ import annotations

import sys
from importlib import import_module, reload

import pytest

MODULE_NAMES: tuple[str, ...] = (
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


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_is_importable(module_name: str) -> None:
    """Ensure each package stub can be imported successfully."""
    sys.modules.pop(module_name, None)
    if "." in module_name:
        sys.modules.pop(module_name.split(".", 1)[0], None)
    module = import_module(module_name)
    reload(module)
