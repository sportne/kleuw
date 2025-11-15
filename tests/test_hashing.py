"""Tests for the hashing utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kleuw.hashing import compute_file_hash, compute_region_hash


def test_compute_region_hash_normalizes_newlines(tmp_path: Path) -> None:
    sample = "alpha\r\nbeta\rgamma\n\ndelta"
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(sample.encode("utf-8"))

    region_hash = compute_region_hash(file_path)

    expected_text = "alpha\nbeta\ngamma\n\ndelta"
    assert (
        region_hash.value == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    )


def test_compute_region_hash_line_range(tmp_path: Path) -> None:
    file_path = tmp_path / "range.txt"
    file_path.write_text("zero\none\ntwo\nthree\n", encoding="utf-8")

    region_hash = compute_region_hash(file_path, start_line=2, end_line=3)

    expected_text = "one\ntwo"
    assert (
        region_hash.value == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    )


def test_compute_region_hash_invalid_ranges(tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.txt"
    file_path.write_text("only\nthree\nlines", encoding="utf-8")

    with pytest.raises(ValueError):
        compute_region_hash(file_path, start_line=0)
    with pytest.raises(ValueError):
        compute_region_hash(file_path, end_line=2)
    with pytest.raises(ValueError):
        compute_region_hash(file_path, start_line=5)
    with pytest.raises(ValueError):
        compute_region_hash(file_path, start_line=2, end_line=1)


def test_compute_file_hash_binary_data(tmp_path: Path) -> None:
    payload = b"\xfffoo\r\nbar\x00baz"
    file_path = tmp_path / "payload.bin"
    file_path.write_bytes(payload)

    digest = compute_file_hash(file_path)

    assert digest.value == hashlib.sha256(payload).hexdigest()
