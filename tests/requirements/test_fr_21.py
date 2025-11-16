"""Requirement tests for FR-21 (stale link detection)."""

from __future__ import annotations

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.model import LineSpan, Link, LinkType, Target
from kleuw.staleness import check_link_staleness


def test_fr_21_marks_links_stale_on_hash_mismatch(tmp_path: Path) -> None:
    """FR-21: Kleuw shall mark links as stale when hashes diverge."""

    src_file = tmp_path / "src.txt"
    dst_file = tmp_path / "dst.txt"
    src_file.write_text("alpha\n", encoding="utf-8")
    dst_file.write_text("omega\n", encoding="utf-8")

    original_src_hash = compute_region_hash(src_file, start_line=1, end_line=1)
    dst_hash = compute_region_hash(dst_file, start_line=1, end_line=1)
    link = Link(
        id="link-1",
        type=LinkType.IMPLEMENTS,
        src=Target(
            path=str(src_file),
            lines=LineSpan(start=1, end=1),
            region_hash=original_src_hash,
        ),
        dst=Target(
            path=str(dst_file),
            lines=LineSpan(start=1, end=1),
            region_hash=dst_hash,
        ),
    )

    src_file.write_text("beta\n", encoding="utf-8")
    result = check_link_staleness(link)

    assert result.stale is True
    assert result.reasons == ("src region changed",)
    assert result.src.stale is True
    assert result.src.reason == "src region changed"
