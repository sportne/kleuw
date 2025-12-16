"""Hashing utilities for Kleuw.

These helpers implement the normalization and hashing behavior described in
``spec/kleuw_staleness.md``.
"""

from __future__ import annotations

from hashlib import new as new_hash
from os import PathLike
from pathlib import Path
from typing import Final

from .model import HashDigest, RegionHash

__all__ = [
    "DEFAULT_HASH_ALGORITHM",
    "compute_region_hash",
    "compute_file_hash",
]

DEFAULT_HASH_ALGORITHM: Final[str] = "sha256"


def compute_region_hash(
    file_path: str | PathLike[str],
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    algo: str = DEFAULT_HASH_ALGORITHM,
) -> RegionHash:
    """Compute a hash for the selected region of ``file_path``.

    Args:
        file_path: Path to the text file containing the region.
        start_line: Optional 1-based start line. When omitted the entire file is
            hashed. When provided without ``end_line`` only ``start_line`` is
            hashed.
        end_line: Optional 1-based inclusive end line. Must be greater than or
            equal to ``start_line`` when both are provided.
        algo: Hash algorithm name understood by :mod:`hashlib`.

    Returns:
        RegionHash: Hash digest describing the selected region.

    Raises:
        ValueError: If the requested line range is invalid or out of bounds.
        FileNotFoundError: If ``file_path`` cannot be opened.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
        ValueError: If ``algo`` is not a valid hash algorithm name.
    """

    if end_line is not None and start_line is None:
        raise ValueError("end_line cannot be provided without start_line.")

    normalized_start = start_line
    if normalized_start is not None and normalized_start < 1:
        raise ValueError("start_line must be >= 1.")

    normalized_end = end_line if end_line is not None else normalized_start
    if (
        normalized_start is not None
        and normalized_end is not None
        and normalized_end < normalized_start
    ):
        raise ValueError("end_line must be >= start_line when both are provided.")

    path = Path(file_path)
    with path.open("r", encoding="utf-8") as handle:
        file_text = handle.read()

    lines = file_text.splitlines()
    if normalized_start is None:
        region_lines = lines
    else:
        start_index = normalized_start - 1
        if start_index >= len(lines):
            raise ValueError("start_line is beyond the end of the file.")
        end_index = normalized_end if normalized_end is not None else normalized_start
        if end_index is None:
            end_index = normalized_start
        if end_index > len(lines):
            raise ValueError("end_line is beyond the end of the file.")
        region_lines = lines[start_index:end_index]

    region_text = "\n".join(region_lines)
    digest = new_hash(algo)
    digest.update(region_text.encode("utf-8"))
    return RegionHash(algo=algo, value=digest.hexdigest())


def compute_file_hash(
    file_path: str | PathLike[str],
    *,
    algo: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = 1024 * 1024,
) -> HashDigest:
    """Compute a hash for the raw bytes of ``file_path``.

    Args:
        file_path: Path to the file to hash.
        algo: Hash algorithm name understood by :mod:`hashlib`.
        chunk_size: Number of bytes to read per iteration. Defaults to 1 MiB.

    Returns:
        HashDigest: Hash of the full file contents.

    Raises:
        FileNotFoundError: If ``file_path`` cannot be opened.
        ValueError: If ``algo`` is not a valid hash algorithm name.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    path = Path(file_path)
    digest = new_hash(algo)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return HashDigest(algo=algo, value=digest.hexdigest())
