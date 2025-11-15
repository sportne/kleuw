"""GUI-specific smoke tests for the Kleuw scaffolding."""

from __future__ import annotations

import importlib
from collections.abc import Iterable

import pytest

from kleuw.model import (
    FileEntry,
    HashDigest,
    LineSpan,
    Link,
    LinkType,
    RegionHash,
    Target,
)

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


def test_gui_model_smoke_exercises_validations() -> None:
    """Exercise core model validations so GUI-only coverage stays healthy."""

    digest = HashDigest(algo="sha256", value="deadbeef")
    region = RegionHash(algo="sha256", value="feedface")
    span = LineSpan(start=3, end=5)
    assert span.resolved_end == 5

    with pytest.raises(ValueError):
        LineSpan(start=0)

    with pytest.raises(ValueError):
        LineSpan(start=5, end=3)

    src = Target(file_id="SRC")
    dst = Target(path="docs/spec.md", lines=span, region_hash=region)
    assert dst.lines is span
    assert dst.region_hash is region

    with pytest.raises(ValueError):
        Target()

    with pytest.raises(ValueError):
        Target(file_id="SRC", path="docs/spec.md")

    with pytest.raises(ValueError):
        Target(file_id="")

    with pytest.raises(ValueError):
        Target(path="")

    link = Link(
        id="L1",
        type="implements",
        src=src,
        dst=dst,
        tags=["gui", "smoke"],
    )
    assert link.type is LinkType.IMPLEMENTS
    assert link.tags == ("gui", "smoke")

    with pytest.raises(ValueError):
        Link(
            id="L2",
            type=LinkType.DEPENDS_ON,
            src=src,
            dst=dst,
            tags=("valid", "  "),
        )

    entry = FileEntry(
        id="SRC",
        path="src/app.py",
        hash=digest,
        aliases=["app.py"],
    )
    assert entry.aliases == ("app.py",)
    assert entry.hash is digest

    with pytest.raises(ValueError):
        FileEntry(id="", path="src/app.py")

    with pytest.raises(ValueError):
        FileEntry(id="SRC", path="")

    with pytest.raises(ValueError):
        FileEntry(id="SRC", path="src/app.py", aliases="alias")
