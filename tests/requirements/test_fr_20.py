"""Requirement tests for FR-20 (staleness hash recomputation)."""

from __future__ import annotations

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.model import LineSpan, Target
from kleuw.staleness import check_target_staleness


def test_fr_20_recomputes_region_hashes(tmp_path: Path) -> None:
    """FR-20: Kleuw shall recompute region hashes and compare stored values."""

    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("alpha\n", encoding="utf-8")
    stored_hash = compute_region_hash(tracked_file, start_line=1, end_line=1)
    target = Target(
        path=str(tracked_file),
        lines=LineSpan(start=1, end=1),
        region_hash=stored_hash,
    )

    tracked_file.write_text("beta\n", encoding="utf-8")
    result = check_target_staleness(target)

    assert result.stale is True
    assert result.reason == "region changed"
    assert result.computed_hash == compute_region_hash(
        tracked_file, start_line=1, end_line=1
    )
