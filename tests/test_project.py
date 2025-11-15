"""Tests for the Project façade helpers."""

import pytest

from kleuw.model import FileEntry, HashDigest, LineSpan, Link, RegionHash, Target
from kleuw.project import Project


def test_add_file_and_find_helpers() -> None:
    project = Project()
    stored = project.add_file(
        FileEntry(
            id="SRC",
            path="src/app.py",
            lang="python",
            aliases=["app.py"],
            hash=HashDigest(algo="sha256", value="1234567890abcdef"),
        )
    )

    assert project.find_file_by_id("SRC") is stored
    assert project.find_file_by_path("src/app.py") is stored
    assert stored["aliases"] == ["app.py"]
    assert project.find_file_by_id("MISSING") is None


def test_add_file_with_full_mapping_fields() -> None:
    project = Project()
    stored = project.add_file(
        {
            "id": "DOC",
            "path": "docs/spec.md",
            "hash": {"algo": "sha512", "value": "abcdef1234567890"},
            "lang": "markdown",
            "note": "Spec file",
            "aliases": ["spec"],
        }
    )

    assert stored["hash"] == {"algo": "sha512", "value": "abcdef1234567890"}
    assert stored["lang"] == "markdown"
    assert stored["note"] == "Spec file"
    assert stored["aliases"] == ["spec"]


def test_add_file_rejects_duplicate_ids() -> None:
    project = Project()
    project.add_file({"id": "SRC", "path": "src/app.py"})

    with pytest.raises(ValueError):
        project.add_file({"id": "SRC", "path": "src/other.py"})


def test_add_link_from_dataclasses() -> None:
    project = Project()
    project.add_file(FileEntry(id="SRC", path="src/app.py"))
    project.add_file(FileEntry(id="DOC", path="docs/spec.md"))

    link = Link(
        id="L1",
        type="implements",
        src=Target(
            file_id="SRC",
            lines=LineSpan(start=10, end=12),
            region_hash=RegionHash(algo="sha256", value="abcdef1234567890"),
        ),
        dst=Target(
            file_id="DOC",
            lines=LineSpan(start=1),
            region_hash=RegionHash(algo="sha512", value="fedcba0987654321"),
        ),
        directed=False,
        tags=("req",),
        note="demo",
    )

    stored = project.add_link(link)

    assert project.find_link_by_id("L1") is stored
    assert stored["directed"] is False
    assert stored["src"]["lines"] == {"start": 10, "end": 12}
    assert stored["dst"]["lines"] == {"start": 1}
    assert stored["src"]["src_region_hash"] == {
        "algo": "sha256",
        "value": "abcdef1234567890",
    }
    assert stored["dst"]["dst_region_hash"] == {
        "algo": "sha512",
        "value": "fedcba0987654321",
    }
    assert stored["tags"] == ["req"]
    assert stored["note"] == "demo"


def test_add_link_from_mapping_with_metadata() -> None:
    project = Project()
    project.add_file(FileEntry(id="SRC", path="src/app.py"))

    stored = project.add_link(
        {
            "id": "L2",
            "type": "documents",
            "src": {
                "file_id": "SRC",
                "lines": {"start": 2, "end": 5},
                "region_hash": {"algo": "sha256", "value": "1234567890abcdef"},
            },
            "dst": {
                "path": "docs/spec.md",
                "lines": {"start": 1, "end": 3},
                "dst_region_hash": {
                    "algo": "sha512",
                    "value": "fedcba0987654321",
                },
            },
            "directed": True,
            "created": "2024-01-02",
            "author": "tester",
            "tags": ["alpha", "beta"],
            "note": "docs",
        }
    )

    assert stored["created"] == "2024-01-02"
    assert stored["author"] == "tester"
    assert stored["src"]["src_region_hash"]["algo"] == "sha256"
    assert stored["dst"]["dst_region_hash"]["value"] == "fedcba0987654321"
    assert stored["tags"] == ["alpha", "beta"]


def test_add_link_rejects_unknown_file_id() -> None:
    project = Project()
    project.add_file(FileEntry(id="SRC", path="src/app.py"))

    with pytest.raises(ValueError):
        project.add_link(
            Link(
                id="L2",
                type="relates_to",
                src=Target(file_id="SRC"),
                dst=Target(file_id="DOC"),
            )
        )


def test_add_link_rejects_invalid_tags_type() -> None:
    project = Project()
    project.add_file(FileEntry(id="SRC", path="src/app.py"))
    project.add_file(FileEntry(id="DOC", path="docs/spec.md"))

    with pytest.raises(ValueError):
        project.add_link(
            {
                "id": "L3",
                "type": "relates_to",
                "src": {"file_id": "SRC"},
                "dst": {"file_id": "DOC"},
                "tags": "invalid",
            }
        )


def test_remove_helpers() -> None:
    project = Project()
    project.add_file(FileEntry(id="SRC", path="src/app.py"))
    project.add_file(FileEntry(id="DOC", path="docs/spec.md"))
    project.add_link(
        {
            "id": "L1",
            "type": "relates_to",
            "src": {"file_id": "SRC"},
            "dst": {"path": "docs/spec.md"},
        }
    )

    removed_link = project.remove_link("L1")
    assert removed_link is not None and removed_link["id"] == "L1"
    assert project.find_link_by_id("L1") is None

    removed_file = project.remove_file("SRC")
    assert removed_file is not None and removed_file["id"] == "SRC"
    assert project.find_file_by_id("SRC") is None

    assert project.remove_link("missing") is None
    assert project.remove_file("missing") is None
