"""Requirement validation tests for FR-8 (File Catalog)."""

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.model import Link, LinkType, RegionHash, Target
from kleuw.staleness import check_link_staleness


def _build_link(src: Target, dst: Target) -> Link:
    return Link(id="L1", type=LinkType.IMPLEMENTS, src=src, dst=dst)


def test_fr_8_missing_file_marks_link_stale(tmp_path: Path) -> None:
    """FR-8: missing files cause their links to be reported as stale."""

    existing_file = tmp_path / "dst.txt"
    existing_file.write_text("dst", encoding="utf-8")
    dst_hash = compute_region_hash(existing_file)

    missing_path = tmp_path / "missing.txt"
    src_target = Target(
        path=str(missing_path),
        region_hash=RegionHash(algo="sha256", value="0" * 64),
    )
    dst_target = Target(path=str(existing_file), region_hash=dst_hash)

    result = check_link_staleness(_build_link(src_target, dst_target))

    assert result.stale is True
    assert result.reasons == ("file missing",)


def test_fr_8_decode_error_marks_link_stale(tmp_path: Path) -> None:
    """FR-8: undecodable files are also treated as stale."""

    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\xff\xff")
    src_target = Target(
        path=str(binary_file),
        region_hash=RegionHash(algo="sha256", value="0" * 64),
    )

    dst_file = tmp_path / "dst.txt"
    dst_file.write_text("dst", encoding="utf-8")
    dst_hash = compute_region_hash(dst_file)
    dst_target = Target(path=str(dst_file), region_hash=dst_hash)

    result = check_link_staleness(_build_link(src_target, dst_target))

    assert result.stale is True
    assert result.reasons == ("decode error",)
