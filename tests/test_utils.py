"""Tests for shared utilities."""

from __future__ import annotations

from pathlib import Path

from kleuw.utils import collect_files_in_directory


def test_collect_files_in_directory_returns_sorted_paths(tmp_path: Path) -> None:
    root_dir = tmp_path / "root"
    nested_dir = root_dir / "nested"
    nested_dir.mkdir(parents=True)
    file_a = root_dir / "alpha.txt"
    file_b = nested_dir / "beta.txt"
    file_a.write_text("alpha")
    file_b.write_text("beta")

    results = collect_files_in_directory(root_dir)

    assert results == [file_a, file_b]


def test_collect_files_in_directory_handles_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    assert collect_files_in_directory(missing) == []
