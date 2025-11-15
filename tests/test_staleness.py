"""Tests for the staleness detection helpers."""

from __future__ import annotations

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.model import LineSpan, Link, LinkType, RegionHash, Target
from kleuw.staleness import check_link_staleness, check_target_staleness


def test_check_target_staleness_reports_fresh_region(tmp_path: Path) -> None:
    file_path = tmp_path / "fresh.txt"
    file_path.write_text("alpha\nbeta\n", encoding="utf-8")

    stored_hash = compute_region_hash(file_path, start_line=1, end_line=2)
    target = Target(
        path=str(file_path),
        lines=LineSpan(start=1, end=2),
        region_hash=stored_hash,
    )

    result = check_target_staleness(target)

    assert result.stale is False
    assert result.reason is None
    assert result.computed_hash == stored_hash


def test_check_link_staleness_detects_src_change(tmp_path: Path) -> None:
    src_file = tmp_path / "src.txt"
    dst_file = tmp_path / "dst.txt"
    src_file.write_text("alpha\n", encoding="utf-8")
    dst_file.write_text("omega\n", encoding="utf-8")

    src_hash = compute_region_hash(src_file)
    dst_hash = compute_region_hash(dst_file)
    link = Link(
        id="L1",
        type=LinkType.REFERS_TO,
        src=Target(path=str(src_file), region_hash=src_hash),
        dst=Target(path=str(dst_file), region_hash=dst_hash),
    )

    src_file.write_text("beta\n", encoding="utf-8")

    result = check_link_staleness(link)

    assert result.stale is True
    assert result.reasons == ("src region changed",)
    assert result.src.reason == "src region changed"
    assert result.dst.stale is False
    assert result.src.computed_hash == compute_region_hash(src_file)


def test_check_target_staleness_handles_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.txt"
    target = Target(
        path=str(missing_path),
        region_hash=RegionHash(algo="sha256", value="0" * 64),
    )

    result = check_target_staleness(target)

    assert result.stale is True
    assert result.reason == "file missing"
    assert result.computed_hash is None


def test_check_target_staleness_handles_invalid_line_range(tmp_path: Path) -> None:
    file_path = tmp_path / "short.txt"
    file_path.write_text("only one line", encoding="utf-8")
    target = Target(
        path=str(file_path),
        lines=LineSpan(start=5),
        region_hash=RegionHash(algo="sha256", value="1" * 64),
    )

    result = check_target_staleness(target)

    assert result.stale is True
    assert result.reason == "invalid line range"


def test_check_target_staleness_handles_decode_errors(tmp_path: Path) -> None:
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(b"\xff\xff")
    target = Target(
        path=str(file_path),
        region_hash=RegionHash(algo="sha256", value="2" * 64),
    )

    result = check_target_staleness(target)

    assert result.stale is True
    assert result.reason == "decode error"


def test_check_link_staleness_reports_missing_hash(tmp_path: Path) -> None:
    file_path = tmp_path / "hash.txt"
    file_path.write_text("delta", encoding="utf-8")
    dst_hash = compute_region_hash(file_path)
    link = Link(
        id="L2",
        type=LinkType.REFERS_TO,
        src=Target(path=str(file_path)),
        dst=Target(path=str(file_path), region_hash=dst_hash),
    )

    result = check_link_staleness(link)

    assert result.stale is True
    assert result.reasons == ("src region hash missing",)
    assert result.src.reason == "src region hash missing"
    assert result.dst.stale is False
