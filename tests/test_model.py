"""Tests for the Kleuw data model dataclasses."""

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


def test_hash_digest_requires_hex() -> None:
    digest = HashDigest(algo="sha256", value="abcdef")
    assert digest.algo == "sha256"
    assert digest.value == "abcdef"

    with pytest.raises(ValueError):
        HashDigest(algo="sha256", value="xyz")


def test_region_hash_inherits_hash_digest() -> None:
    region = RegionHash(algo="sha512", value="1234")
    assert isinstance(region, HashDigest)


def test_line_span_validations() -> None:
    span = LineSpan(start=10)
    assert span.resolved_end == 10

    span_with_end = LineSpan(start=5, end=8)
    assert span_with_end.resolved_end == 8

    with pytest.raises(ValueError):
        LineSpan(start=0)

    with pytest.raises(ValueError):
        LineSpan(start=5, end=4)


def test_target_requires_single_identifier() -> None:
    src = Target(file_id="APP")
    assert src.file_id == "APP"
    assert src.path is None

    dst = Target(path="docs/spec.md", lines=LineSpan(start=1))
    assert dst.path == "docs/spec.md"

    with pytest.raises(ValueError):
        Target()

    with pytest.raises(ValueError):
        Target(file_id="APP", path="docs/spec.md")


def test_link_normalizes_inputs() -> None:
    link = Link(
        id="L1",
        type="implements",
        src=Target(file_id="APP"),
        dst=Target(path="docs/spec.md"),
        tags=["req", "v1"],
    )

    assert link.type is LinkType.IMPLEMENTS
    assert link.tags == ("req", "v1")

    with pytest.raises(ValueError):
        Link(
            id="L2",
            type=LinkType.IMPLEMENTS,
            src=Target(file_id="APP"),
            dst=Target(path="docs/spec.md"),
            tags="invalid",
        )


def test_file_entry_validations() -> None:
    digest = HashDigest(algo="sha256", value="1234")
    entry = FileEntry(
        id="APP",
        path="src/app.py",
        hash=digest,
        aliases=["app.py"],
    )

    assert entry.aliases == ("app.py",)
    assert entry.hash is digest

    with pytest.raises(ValueError):
        FileEntry(id="", path="src/app.py")

    with pytest.raises(ValueError):
        FileEntry(id="APP", path="", aliases=["alias"])

    with pytest.raises(ValueError):
        FileEntry(id="APP", path="src/app.py", aliases="alias")
