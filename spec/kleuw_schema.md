# Kleuw Data Format & Schema Specification

[Back to Overview](kleuw_overall_spec.md)

## 1. Purpose

This document defines the **data model**, **JSON structure**, and **schema rules** used by Kleuw for storing project information, file metadata, and link relationships.

The schema is written for human comprehension and implementation guidance—it is not a JSON Schema syntax file, but a conceptual and structural specification.

For a formal JSON Schema draft, a separate `kleuw.schema.json` will be produced later using these rules.

---

## 2. High-Level Structure

A Kleuw project file is a **single JSON object** with three major sections:

```json
{
  "version": 1,
  "files": [ ... ],
  "links": [ ... ],
  "metadata": { ... }
}
```

### 2.1 Required Fields

| Field     | Type    | Description                                 |
| --------- | ------- | ------------------------------------------- |
| `version` | integer | Schema version (must be 1)                  |
| `files`   | array   | Metadata for known files in the project     |
| `links`   | array   | All relationships captured by the user/tool |

### 2.2 Optional Fields

| Field      | Type   | Description                                                    |
| ---------- | ------ | -------------------------------------------------------------- |
| `metadata` | object | Arbitrary document metadata (author, tool version, timestamps) |

---

## 3. File Entries

Each object in the `files` array represents a file known to the project.

### 3.1 File Object Structure

```json
{
  "id": "APP",
  "path": "src/App.java",
  "hash": { "algo": "sha256", "value": "abc123..." },
  "lang": "java",
  "note": "optional description",
  "aliases": ["old/path/App.java"]
}
```

### 3.2 Field Definitions

| Field     | Type             | Required | Description                                 |
| --------- | ---------------- | -------- | ------------------------------------------- |
| `id`      | string           | yes      | Stable identifier unique within the project |
| `path`    | string           | yes      | Canonical path to file                      |
| `hash`    | object           | no       | Optional whole-file hash                    |
| `lang`    | string           | no       | Language hint (e.g., "c", "java", "md")     |
| `note`    | string           | no       | Free-form note                              |
| `aliases` | array of strings | no       | Additional paths referring to the same file |

### 3.3 Notes

* Either `id` or `path` can be used in link targets.
* It's recommended (not required) to populate `files[]` before creating links.

---

## 4. Relationship Links

Each entry in `links` represents a directed or undirected relationship between two text regions.

### 4.1 Link Object Structure

```json
{
  "id": "L1",
  "type": "implements",
  "src": {
    "file_id": "APP",
    "lines": { "start": 40, "end": 75 },
    "src_region_hash": { "algo": "sha256", "value": "9af2..." }
  },
  "dst": {
    "path": "docs/spec.md",
    "lines": { "start": 120, "end": 150 },
    "dst_region_hash": { "algo": "sha256", "value": "1b72..." }
  },
  "directed": true,
  "created": "2025-11-10T15:20:00Z",
  "author": "s.portner",
  "tags": ["reqtrace", "v1"],
  "note": "Spec §3.2 → App.start()"
}
```

---

## 4.2 Link Field Definitions

| Field      | Type                  | Required          | Description                           |
| ---------- | --------------------- | ----------------- | ------------------------------------- |
| `id`       | string                | yes               | Unique link identifier                |
| `type`     | string (enum)         | yes               | One of the allowed relationship types |
| `src`      | object                | yes               | Source target                         |
| `dst`      | object                | yes               | Destination target                    |
| `directed` | boolean               | no (default true) | Whether link is directional           |
| `created`  | string (ISO datetime) | no                | Creation timestamp                    |
| `author`   | string                | no                | Metadata only                         |
| `tags`     | array                 | no                | Free-form non-whitespace labels       |
| `note`     | string                | no                | Free text, comments, rationale        |

---

## 5. Relationship Types (Enumerated)

The `type` field must be one of:

```
refers_to
defines
declares
implements
tests
depends_on
duplicates
mentions
fixes
blocks
derives_from
verifies
builds
documents
relates_to
```

This list has the following properties:

* Stable for Kleuw schema v1
* May be extended in schema v2
* Disallows arbitrary relationship strings

---

## 6. Target Objects

A `src` or `dst` object describes **where** a link points.

### 6.1 Structure

A target can reference either a file by ID *or* by path:

```json
{
  "file_id": "APP",
  "lines": { "start": 10, "end": 20 }
}
```

OR

```json
{
  "path": "docs/design.md",
  "lines": { "start": 1 }
}
```

### 6.2 Allowed Keys

| Key                                   | Type   | Required                      | Description                 |
| ------------------------------------- | ------ | ----------------------------- | --------------------------- |
| `file_id`                             | string | required if `path` omitted    | Reference to project file   |
| `path`                                | string | required if `file_id` omitted | Direct path fallback        |
| `lines`                               | object | no                            | Line span (single or range) |
| `src_region_hash` / `dst_region_hash` | object | no                            | Stored region hash          |

Target objects MUST NOT contain both `file_id` and `path`.

---

## 7. Line Span Objects

The `lines` field defines a **1-based inclusive span**:

```json
{ "start": 40, "end": 75 }
```

If `end` is omitted or null, it equals `start` (single line).

### Requirements:

* `start` ≥ 1
* `end` ≥ `start`
* Integers only

Future versions may add support for multi-span lists.

---

## 8. Region Hash Objects

Each region hash is:

```json
{
  "algo": "sha256",
  "value": "1b72f3e..."
}
```

### Requirements

| Field   | Type       | Description                               |
| ------- | ---------- | ----------------------------------------- |
| `algo`  | string     | Hash algorithm (`sha256`, `sha512`, etc.) |
| `value` | hex string | Hash digest in hex encoding               |

Hashes must follow the staleness rules in the staleness specification.

---

## 9. Metadata Object

```json
{
  "author": "kleuw-cli/0.1.0",
  "created": "2025-11-11T10:00:00Z"
}
```

Metadata is free-form and ignored by the core logic.

---

## 10. Validation Rules

### 10.1 Structural

* `version` must equal **1**.
* `files` and `links` must be arrays.
* No unknown top-level fields.

### 10.2 File Constraints

* `id` must be unique.
* `path` must be non-empty.
* `hash.value` must be valid hex.

### 10.3 Link Constraints

* `id` must be unique.
* `type` must be in the allowed enumeration.
* Exactly **one** of `file_id` or `path` must appear in a target.
* If `file_id` is used, it must match a file entry.
* `lines` must adhere to span rules.
* `src_region_hash` and `dst_region_hash` must follow hash rules.

### 10.4 Semantic

* Line spans must fall within file bounds when checking staleness.
* Paths must be portable (prefer POSIX).

---

## 11. Example Minimal Project

```json
{
  "version": 1,
  "files": [],
  "links": []
}
```

---

## 12. Example Full Project

```json
{
  "version": 1,
  "files": [
    {
      "id": "APP",
      "path": "src/App.java",
      "hash": { "algo": "sha256", "value": "8143d9..." },
      "lang": "java"
    },
    {
      "id": "SPEC",
      "path": "docs/spec.md",
      "lang": "md"
    }
  ],
  "links": [
    {
      "id": "L1",
      "type": "implements",
      "src": {
        "file_id": "APP",
        "lines": {"start": 40, "end": 75},
        "src_region_hash": { "algo": "sha256", "value": "e9fa..." }
      },
      "dst": {
        "file_id": "SPEC",
        "lines": {"start": 120, "end": 150},
        "dst_region_hash": { "algo": "sha256", "value": "2df1..." }
      },
      "directed": true,
      "created": "2025-11-11T15:30:00Z",
      "author": "s.portner",
      "tags": ["reqtrace"],
      "note": "Spec to implementation mapping"
    }
  ]
}
```

---

## 13. Schema Validation Implementation

`src/kleuw/schema.py` loads the authoritative JSON Schema from
`spec/kleuw.schema.json` and enforces the structural rules described above. The
module:

* Rejects unknown top-level keys as well as extraneous fields inside file/link objects.
* Verifies unique `id` values for both files and links.
* Ensures `tags` are non-empty strings without whitespace, and that region-hash
  objects contain `algo`/`value` pairs with ≥16 hexadecimal characters.
* Enforces the mutually exclusive `file_id` vs `path` rule for targets while also
  validating line spans.

Both `load_project` and `save_project` call `validate_project` so that every IO
operation performs round-trip validation. The CLI `validate` subcommand exposes
the same checks directly to users.

## 14. Future Schema Extensions (Not in v1)

* Discontiguous line spans
* Line-level text anchors based on regex signatures
* Internal link grouping or hierarchy
* Versioned region histories
* Structured metadata for requirement IDs, test cases, issue numbers

---

[Back to Overview](kleuw_overall_spec.md)
