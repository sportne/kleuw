"""Shared utility helpers for Kleuw."""

from __future__ import annotations

from pathlib import Path

__all__ = ["collect_files_in_directory"]


def collect_files_in_directory(directory: Path) -> list[Path]:
    """Collect files within a directory tree.

    Args:
        directory: Root directory to scan.

    Returns:
        A sorted list of file paths contained in the directory. Returns an
        empty list if the directory cannot be read.
    """

    if not directory.is_dir():
        return []
    files: list[Path] = []
    try:
        for path in directory.rglob("*"):
            if path.is_file():
                files.append(path)
    except OSError:
        return []
    return sorted(files, key=lambda item: str(item))
