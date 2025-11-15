# Kleuw Staleness & Hashing Specification

[Back to Overview](kleuw_overall_spec.md)

## 1. Purpose

This document defines the rules and procedures governing **staleness detection**, **region hashing**, and **file hashing** within the Kleuw system. It establishes how Kleuw determines whether a captured relationship has become invalid due to file changes.

The staleness model applies to both CLI and GUI operations and must be implemented consistently across both.

---

## 2. Terminology

* **Region:** The selection of text lines referenced by a link's `src` or `dst` target.
* **Region Hash:** A cryptographic hash of the exact text of the region at the time the link was created or last updated.
* **Stale Link:** A link whose current region hash does not match the stored region hash.
* **Whole-file Link:** A link where no explicit line range is selected; the region is the entire file.
* **Normalization:** A deterministic process for extracting the text region to be hashed.

---

## 3. Goals of the Staleness System

* Provide **precise drift detection** for referenced regions.
* Distinguish between **relevant and irrelevant** file changes.
* Maintain a stable baseline for hashing across platforms.
* Support both GUI and CLI workflows.
* Operate using only Python standard library.

---

## 4. Hashing Overview

Kleuw computes two classes of hashes:

### 4.1 File Hash (Optional)

* Applied to the whole raw file (binary).
* Useful for quick high-level drift diagnosis, but **not used directly** to determine staleness.

### 4.2 Region Hash (Required for Links)

Each link stores two region hashes:

* `src_region_hash`
* `dst_region_hash`

A region hash must:

* Accurately reflect only the referenced region.
* Remain stable as long as the selected region’s text is unchanged.
* Change whenever any character inside the region changes.

---

## 5. Region Normalization Rules

When computing region hashes, Kleuw applies strict normalization.
These rules guarantee cross-platform consistency.

### 5.1 Text Loading

* Read file in **text mode**, using UTF-8.
* Apply **universal newline mode** (platform-agnostic):

  * All `\r\n` → `\n`
  * All bare `\r` → `\n`

### 5.2 Line Handling

* Lines are counted starting at **1**.
* A region may be:

  * a single line (`start = end`),
  * a range of lines (`start`–`end` inclusive),
  * or whole file (no range).
* Region extraction:

  * `lines[start-1 : end]` from the normalized list.

### 5.3 Concatenation

* Join extracted lines using `"\n"`.
* **Do not** append an extra newline at the end.
* **Do not** strip whitespace.
* **Do not** modify indentation.
* **Do not** trim trailing whitespace.

### 5.4 Encoding & Hashing

* Encode final region string as **UTF-8**.
* Compute digest using algorithm specified in the JSON schema (default: `sha256`).

---

## 6. Staleness Determination

A link is considered **stale** if any of the following are true:

1. The file referenced in `src` or `dst` cannot be opened.
2. The region cannot be extracted due to out-of-range lines.
3. The newly computed region hash differs from the stored hash.

If none of these conditions are true, the link is **fresh**.

### 6.1 Multi-Channel Reporting

The staleness system supports:

* GUI indicators (highlighted rows, status bar summaries)
* CLI command `kleuw check`
* Human-readable output
* JSON output (`--json`)

---

## 7. Link Update Behavior

### 7.1 Recompute Hashes

* User may explicitly recompute stored region hashes.
* Overwrites old hashes and sets new staleness baseline.

### 7.2 Editing Line Ranges

* Changing the line range counts as a structural change.
* Hashes are recomputed automatically.

---

## 8. Region Hash Storage Format

The JSON schema provides:

```json
{
  "src_region_hash": {
    "algo": "sha256",
    "value": "abcdef1234..."
  }
}
```

Same structure applies to `dst_region_hash`.

### 8.1 Requirements

* `algo` shall match a hash algorithm recognized by Python's `hashlib`.
* `value` shall be a lowercase or uppercase hex string.
* Hex digest must be at least 16 hex characters.

---

## 9. File Hashing (Optional Feature)

Kleuw may store whole-file hashes in the `files` array:

```json
{
  "id": "APP",
  "path": "app/App.java",
  "hash": {
    "algo": "sha256",
    "value": "deadbeef..."
  }
}
```

This is optional and does **not** affect link freshness, but:

* It gives a quick indication when any change occurred in a file.
* Helps developers prioritize links that need checking.

---

## 10. CLI Staleness Behavior

### 10.1 Command

```
kleuw check <project.json> [--link-id LID...] [--json]
```

### 10.2 Exit Codes

* **0** — all links fresh
* **1** — at least one stale

### 10.3 JSON Structure (Example)

```json
{
  "total": 37,
  "stale": 4,
  "results": [
    { "id": "L1", "stale": true,  "reason": "src changed" },
    { "id": "L2", "stale": false }
  ]
}
```

---

## 11. GUI Staleness Behavior

### 11.1 Visual Indicators

* Stale rows highlighted (yellow or orange)
* Tooltip contains detailed reason:

  * "src region changed"
  * "dst region changed"
  * "file missing"
  * "lines out of range"

### 11.2 Staleness Dialog

After clicking **Check Staleness**:

```
Staleness Check Complete
------------------------
Total Links: N
Stale Links: M
```

Button: **View Stale Links** applies filter to Links Panel.

---

## 12. Performance Considerations

* Hashing should scale linearly with selected region size.
* Reading file lines should be streamed when possible.
* Projects with 500+ links should be processed in <3 seconds.

---

## 13. Error Handling

* **Missing file** → stale ("file missing")
* **Invalid UTF-8** → stale ("decode error")
* **Invalid range** → stale ("invalid line range")
* **Hash mismatch** → stale ("src/dst changed")

---

## 14. Future Extensions (Not in v1)

* Multi-span line selection
* Cryptographic hash hardening (BLAKE3 if dependency allowed)
* Binary region linking
* Historical version tracking
* Region diff previews

---

[Back to Overview](kleuw_overall_spec.md)
