"""Requirement validation tests for FR-3."""

from __future__ import annotations

from kleuw import schema

VALID_PROJECT = {
    "version": 1,
    "files": [
        {
            "id": "file-1",
            "path": "README.md",
        }
    ],
    "links": [
        {
            "id": "link-1",
            "type": "refers_to",
            "src": {
                "file_id": "file-1",
                "lines": {"start": 1, "end": 2},
                "src_region_hash": {"algo": "sha256", "value": "a" * 64},
            },
            "dst": {
                "file_id": "file-1",
                "lines": {"start": 3, "end": 4},
                "dst_region_hash": {"algo": "sha256", "value": "b" * 64},
            },
        }
    ],
}


def test_fr_3_structurally_valid_project_passes_validation() -> None:
    """FR-3: schema validation accepts compliant structures."""

    errors = schema.validate_project(VALID_PROJECT)
    assert errors == []


def test_fr_3_detects_structural_violations() -> None:
    """FR-3: schema validation flags missing paths and unknown references."""

    invalid = {
        "version": 1,
        "files": [
            {
                "id": "file-1",
                # missing path should be reported
            }
        ],
        "links": [
            {
                "id": "link-1",
                "type": "refers_to",
                "src": {
                    "file_id": "file-1",
                    "lines": {"start": 1, "end": 1},
                    "src_region_hash": {"algo": "sha256", "value": "c" * 64},
                },
                "dst": {
                    "file_id": "file-2",
                    "lines": {"start": 2, "end": 2},
                    "dst_region_hash": {"algo": "sha256", "value": "d" * 64},
                },
            }
        ],
    }

    errors = schema.validate_project(invalid)

    assert errors, "Expected validation to report structural errors"
    assert any("path" in error for error in errors)
    assert any("file-2" in error for error in errors)
