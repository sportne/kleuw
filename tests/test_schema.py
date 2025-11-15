"""Tests for the schema validation helpers."""

from __future__ import annotations

from kleuw import schema


def test_load_schema_returns_expected_structure() -> None:
    schema_data = schema.load_schema()
    assert isinstance(schema_data, dict)
    assert schema_data["title"] == "Kleuw Project Schema"


def test_validate_project_accepts_valid_structure() -> None:
    project = {
        "version": 1,
        "files": [
            {
                "id": "APP",
                "path": "src/app.py",
                "hash": {"algo": "sha256", "value": "a" * 16},
            }
        ],
        "links": [
            {
                "id": "L1",
                "type": "implements",
                "src": {
                    "file_id": "APP",
                    "lines": {"start": 1, "end": 2},
                    "src_region_hash": {"algo": "sha256", "value": "b" * 16},
                },
                "dst": {
                    "path": "docs/spec.md",
                    "lines": {"start": 3},
                },
                "directed": True,
                "tags": ["trace"],
            }
        ],
        "metadata": {"author": "kleuw-cli/0.1.0"},
    }

    assert schema.validate_project(project) == []


def test_validate_project_reports_multiple_errors() -> None:
    project = {
        "version": 2,
        "files": [
            {"id": "APP", "path": ""},
            {"id": "APP", "path": "src/duplicate.py"},
        ],
        "links": [
            {
                "id": "L1",
                "type": "unknown",
                "src": {"path": ""},
                "dst": {"file_id": "MISSING"},
            }
        ],
        "extra": True,
    }

    errors = schema.validate_project(project)
    assert errors
    assert any("Field 'version' must equal 1." in message for message in errors)
    assert any("files[0].path must be a non-empty string." in msg for msg in errors)
    assert any("Duplicate file id 'APP'" in msg for msg in errors)
    assert any("links[0].type must be one of:" in msg for msg in errors)
    assert any(
        "links[0].dst.file_id references unknown file id 'MISSING'" in msg
        for msg in errors
    )
    assert any("Unknown top-level field 'extra'." in msg for msg in errors)


def test_validate_project_rejects_incorrect_collection_types() -> None:
    project = {
        "version": "1",
        "files": {},
        "links": {},
        "metadata": [],
    }

    errors = schema.validate_project(project)
    assert any(
        "Field 'version' must be an integer equal to 1." in msg for msg in errors
    )
    assert any(
        "Field 'files' must be an array of file objects." in msg for msg in errors
    )
    assert any(
        "Field 'links' must be an array of link objects." in msg for msg in errors
    )
    assert any(
        "Field 'metadata' must be an object when provided." in msg for msg in errors
    )


def test_validate_project_reports_file_entry_errors() -> None:
    project = {
        "version": 1,
        "files": [
            "not-a-dict",
            {
                "path": "",
                "hash": "not-a-dict",
                "lang": 7,
                "note": 3,
                "aliases": "not-a-list",
                "extra": True,
            },
            {
                "id": "",
                "path": "src/app.py",
                "hash": {"algo": "", "value": "zz"},
                "aliases": ["", 7],
            },
            {
                "id": "FILE4",
                "path": "src/file.py",
                "hash": {},
            },
        ],
        "links": [],
    }

    errors = schema.validate_project(project)
    assert any("files[0] must be an object." in msg for msg in errors)
    assert any("files[1] missing required field 'id'." in msg for msg in errors)
    assert any("files[1].hash must be an object." in msg for msg in errors)
    assert any("files[1].lang must be a string." in msg for msg in errors)
    assert any("files[1].note must be a string." in msg for msg in errors)
    assert any("files[1].aliases must be a list" in msg for msg in errors)
    assert any("files[1] contains unknown field 'extra'." in msg for msg in errors)
    assert any("files[2].id must be a non-empty string." in msg for msg in errors)
    assert any(
        "files[2].hash.algo must be a non-empty string." in msg for msg in errors
    )
    assert any(
        "files[2].hash.value must be at least 16 hex characters." in msg
        for msg in errors
    )
    assert any(
        "files[2].hash.value must contain only hexadecimal characters." in msg
        for msg in errors
    )
    assert any(
        "files[2].aliases[1] must be a non-empty string." in msg for msg in errors
    )
    assert any("files[3].hash missing required field 'algo'." in msg for msg in errors)
    assert any("files[3].hash missing required field 'value'." in msg for msg in errors)


def test_validate_project_reports_link_entry_errors() -> None:
    project = {
        "version": 1,
        "files": [{"id": "APP", "path": "src/app.py"}],
        "links": [
            "not-a-dict",
            {"extra": True},
            {
                "id": "",
                "type": "implements",
                "src": {"file_id": "APP", "path": "duplicate"},
                "dst": {"file_id": "APP", "lines": {"start": 0, "end": -1}},
            },
            {
                "id": "L2",
                "type": 7,
                "src": {
                    "file_id": "APP",
                    "lines": {"end": 3},
                    "src_region_hash": {"algo": "", "value": "short"},
                    "extra": True,
                },
                "dst": {"path": 5, "lines": "not-a-dict"},
                "extra": True,
            },
            {
                "id": "L3",
                "type": "implements",
                "src": {"file_id": "MISSING", "lines": {"start": 0}},
                "dst": {"path": "ok"},
                "directed": "yes",
                "created": 123,
                "author": 456,
                "tags": "not-a-list",
                "note": 789,
            },
            {
                "id": "L3",
                "type": "implements",
                "src": {
                    "path": "ok",
                    "lines": {"start": 2, "end": 1},
                    "src_region_hash": {"algo": "sha256", "value": "g" * 16},
                },
                "dst": {
                    "path": "also ok",
                    "lines": {"start": "one"},
                    "dst_region_hash": {"algo": "sha256", "value": "short"},
                },
                "tags": ["good", "bad tag"],
            },
        ],
    }

    errors = schema.validate_project(project)
    assert any("links[0] must be an object." in msg for msg in errors)
    assert any("links[1] missing required field 'id'." in msg for msg in errors)
    assert any("links[1] contains unknown field 'extra'." in msg for msg in errors)
    assert any("links[2].id must be a non-empty string." in msg for msg in errors)
    assert any(
        "links[2].src must include exactly one of 'file_id' or 'path'." in msg
        for msg in errors
    )
    assert any("links[2].dst.lines.start must be >= 1." in msg for msg in errors)
    assert any("links[2].dst.lines.end must be >= 1." in msg for msg in errors)
    assert any("links[3].type must be a string." in msg for msg in errors)
    assert any("links[3] contains unknown field 'extra'." in msg for msg in errors)
    assert any("links[3].src contains unknown field 'extra'." in msg for msg in errors)
    assert any(
        "links[3].src.lines missing required field 'start'." in msg for msg in errors
    )
    assert any(
        "links[3].src.src_region_hash.algo must be a non-empty string." in msg
        for msg in errors
    )
    assert any("links[3].dst.lines must be an object." in msg for msg in errors)
    assert any(
        "links[4].src.file_id references unknown file id 'MISSING'." in msg
        for msg in errors
    )
    assert any("links[4].src.lines.start must be >= 1." in msg for msg in errors)
    assert any("links[4].directed must be a boolean." in msg for msg in errors)
    assert any("links[4].created must be a string." in msg for msg in errors)
    assert any("links[4].author must be a string." in msg for msg in errors)
    assert any("links[4].tags must be a list" in msg for msg in errors)
    assert any("links[4].note must be a string." in msg for msg in errors)
    assert any("Duplicate link id 'L3'" in msg for msg in errors)
    assert any("links[5].src.lines.end must be >= start." in msg for msg in errors)
    assert any(
        "links[5].src.src_region_hash.value must contain only hexadecimal characters."
        in msg
        for msg in errors
    )
    assert any("links[5].dst.lines.start must be an integer." in msg for msg in errors)
    assert any(
        "links[5].dst.dst_region_hash.value must be at least 16 hex characters." in msg
        for msg in errors
    )
    assert any(
        "links[5].tags[1] must be a non-empty string without whitespace." in msg
        for msg in errors
    )
