"""CLI test helpers shared across requirement validations."""

from __future__ import annotations

from pathlib import Path

from kleuw.hashing import compute_region_hash
from kleuw.io import save_project
from kleuw.model import FileEntry, LineSpan, Link, LinkType, Target
from kleuw.project import Project


def create_project(path: Path) -> Project:
    """Create a minimal project at ``path`` and return it."""

    project = Project()
    save_project(path, project)
    return project


def create_project_with_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a project with tracked SRC/DST files for link operations."""

    project_path = tmp_path / "project.json"
    src_file = tmp_path / "src.txt"
    src_file.write_text("alpha\nbeta\n", encoding="utf-8")
    dst_file = tmp_path / "dst.txt"
    dst_file.write_text("one\ntwo\n", encoding="utf-8")

    project = Project()
    project.add_file(FileEntry(id="SRC", path=str(src_file)))
    project.add_file(FileEntry(id="DST", path=str(dst_file)))
    save_project(project_path, project)
    return project_path, src_file, dst_file


def create_project_with_links(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a project with two links where the second one is stale."""

    project_path = tmp_path / "project.json"
    src_file = tmp_path / "src.txt"
    src_file.write_text("alpha\nbeta\n", encoding="utf-8")
    dst_file = tmp_path / "dst.txt"
    dst_file.write_text("one\ntwo\n", encoding="utf-8")

    project = Project()
    project.add_file(FileEntry(id="file-1", path=str(src_file)))
    project.add_file(FileEntry(id="file-2", path=str(dst_file)))

    src_line1 = compute_region_hash(src_file, start_line=1, end_line=1)
    src_line2 = compute_region_hash(src_file, start_line=2, end_line=2)
    dst_line1 = compute_region_hash(dst_file, start_line=1, end_line=1)

    project.add_link(
        Link(
            id="L1",
            type=LinkType.IMPLEMENTS,
            src=Target(
                file_id="file-1",
                lines=LineSpan(start=1, end=1),
                region_hash=src_line1,
            ),
            dst=Target(
                file_id="file-2",
                lines=LineSpan(start=1, end=1),
                region_hash=dst_line1,
            ),
        )
    )
    project.add_link(
        Link(
            id="L2",
            type=LinkType.TESTS,
            src=Target(
                file_id="file-1",
                lines=LineSpan(start=2, end=2),
                region_hash=src_line2,
            ),
            dst=Target(
                file_id="file-2",
                lines=LineSpan(start=1, end=1),
                region_hash=dst_line1,
            ),
        )
    )

    save_project(project_path, project)
    # Modify the second line so only ``L2`` is stale.
    src_file.write_text("alpha\nchanged\n", encoding="utf-8")
    return project_path, src_file, dst_file
