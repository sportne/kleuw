# Kleuw CLI Specification

[Back to Overview](kleuw_overall_spec.md)

## 1. Purpose

This document defines the **command-line interface (CLI)** for the Kleuw tool.
The CLI enables automation, batch processing, scripted integration, and staleness detection without launching the GUI.

It is implemented entirely with the Python standard library (`argparse`, `json`, `pathlib`, `hashlib`, etc.).

---

## 2. Design Principles

* **Predictable:** Commands use a stable, Unix-style syntax.
* **Composable:** Output can be piped into other tools.
* **Parsable:** Use consistent, machine-readable output for automation.
* **Stdlib Only:** No third-party dependencies.

All commands follow this structure:

```
kleuw <command> [arguments] [options]
```

---

## 3. Commands Overview

| Command       | Purpose                                    |
| ------------- | ------------------------------------------ |
| `init`        | Create a new Kleuw project JSON file       |
| `add-file`    | Add a file entry to the project            |
| `list-files`  | List project files                         |
| `create-link` | Create a link between two files or regions |
| `list-links`  | List all links (optional filters)          |
| `check`       | Check for stale links                      |
| `recompute`   | Update region hashes for selected links    |
| `validate`    | Validate project JSON structure            |
| `export`      | Export summaries (JSON/CSV/plain)          |

---

## 4. Command Specifications

### 4.1 `init`

```
kleuw init <project.json>
```

Creates a new Kleuw project with schema version and empty lists.

**Behavior:**

* Fails if file already exists (unless `--force`).
* Writes minimal valid project:

```json
{
  "version": 1,
  "files": [],
  "links": []
}
```

**Options:**

* `--force` — overwrite existing file

---

### 4.2 `add-file`

```
kleuw add-file <project.json> <path> [--id FILEID]
```

Adds a file entry to the project.

**Behavior:**

* If `--id` is omitted, Kleuw generates the next available `file-<n>` identifier.
* The CLI verifies that the path exists and is a regular file before writing the entry.
* `--hash` computes a `sha256` digest and stores it under the `hash` field.

**Options:**

* `--id` — user-specified file ID
* `--hash` — compute file hash (sha256)

---

### 4.3 `list-files`

```
kleuw list-files <project.json>
```

Prints the list of files in table format with columns `ID`, `PATH`, `LANG`, `HASH`, and `NOTE`.

`--json` outputs a payload of the form:

```json
{
  "files": [ { ... }, ... ]
}
```

**Options:**

* `--json` — output as JSON

---

### 4.4 `create-link`

```
kleuw create-link <project.json> \
    --src <path[:Lstart[-Lend]]> \
    --dst <path[:Lstart[-Lend]]> \
    --type <RELTYPE> \
    [--note "..."] [--tags tag1,tag2]
```

Creates a new link between two targets.

**Behavior:**

* Automatically splits the `path:range` syntax, e.g.

  * `src/app.py:45-60`
  * `src/app.py:120`
* Computes region hashes for the link.
* Resolves `file_id` references when the path matches a recorded file; otherwise stores the path directly.
* Generates the next available `link-<n>` ID and appends the link to the project.
* Trims comma-separated tags supplied via `--tags`; blank values raise an error.

**Options:**

* `--type` — relationship type (enum)
* `--note` — free-form text
* `--tags` — comma-separated labels

**Output:**

* Prints link ID on success

---

### 4.5 `list-links`

```
kleuw list-links <project.json> [--stale-only] [--type RELTYPE]
```

Lists all or filtered links. The command recomputes staleness only when
`--stale-only` is provided; JSON output always mirrors the stored link entries.

**Options:**

* `--json` — machine-readable output
* `--stale-only` — filter
* `--type RELTYPE` — filter by relationship type

---

### 4.6 `check`

```
kleuw check <project.json> [--link-id LID...]
```

Checks for stale relationships.

**Behavior:**

* Recomputes region hashes for selected links or all links.
* Prints tabular diagnostics with columns `ID`, `TYPE`, `STATUS`, `DETAILS`.
* Returns exit code:

  * **0** if no stale links
  * **1** if one or more stale

**Options:**

* `--link-id LID...` — restrict evaluation to a subset of links (errors if an ID is unknown)
* `--json` — output structured results

**Example Output:**

```
ID    TYPE       STATUS   DETAILS
L12   implements STALE    src region changed
L13   tests      OK       -
```

**Example JSON:**

```json
{
  "total": 2,
  "stale": 1,
  "results": [
    { "id": "L12", "type": "implements", "stale": true,  "reason": "src region changed" },
    { "id": "L13", "type": "tests", "stale": false }
  ]
}
```

---

### 4.7 `recompute`

```
kleuw recompute <project.json> [--link-id LID...]
```

Updates stored region hashes to current file state.

**Behavior:**

* Validates the project file before recomputing.
* Requires access to the original source files so hashes can be refreshed.
* Writes the updated hashes back to disk; there is no `--json` mode for this command.

**Use Case:** Accepting updated content as the new baseline.

---

### 4.8 `validate`

```
kleuw validate <project.json>
```

Validates the project against `spec/kleuw.schema.json`.

**Checks:** Structural schema conformity, `file_id` references, line span shape, and hash encoding rules.

**Output:** Prints a summary such as `Project is valid (3 files, 12 links).` when no errors are found. Validation errors are listed on stderr.

Exit codes: **0** when valid, **1** otherwise.

---

### 4.9 `export`

```
kleuw export <project.json> --format {json,csv,txt}
```

Exports:

* File list plus link list annotated with staleness results
* Project summary counts (`total`, `stale`, `exported`)

**Formats:**

* `json` — includes `files`, `links` (with `stale`/`stale_reasons` fields), and a summary block
* `csv` — writes rows with a `section` column (either `file` or `link`) so downstream tooling can split data
* `txt` — renders the same tables used by `list-files`/`check` followed by totals

`--stale` filters the exported links (and summary) to stale entries only.

---

## 5. CLI Pattern Rules

* All commands accept `--json` for machine-readable output when applicable.
* Flags currently use descriptive long forms (`--type`, `--json`, etc.); short aliases may be added later.
* Errors print to STDERR and return non-zero exit codes.
* Commands should never modify project files unless explicitly instructed (`create-link`, `add-file`, `recompute`).

---

## 6. Input Formats

### Region Syntax

```
<path>:<line>
<path>:<start>-<end>
```

Examples:

* `src/module.py:100`
* `docs/spec.md:40-55`

If omitted, the entire file is referenced.

---

## 7. Output Specifications

### 7.1 Table Output

Fixed-width columns for terminals.

### 7.2 JSON Output

Used for:

* `list-files --json`
* `list-links --json`
* `check --json`
* `export --format json`

JSON keys shall match the Kleuw schema’s property names. Notable payload shapes:

* `list-links --json` returns the stored link entries (no derived staleness fields) even when `--stale-only` filters the data.
* `check --json` emits `{ "total": ..., "stale": ..., "results": [ {"id", "type", "stale", "reason"? }, ... ] }`.
* `export --format json` includes `files`, `links` (with `stale`/`stale_reasons`), and a `summary` block.

---

## 8. Error Cases

* Missing project file
* Invalid project JSON
* Invalid region syntax
* File does not exist
* Relationship type not in enum
* Duplicate file or link IDs

Each should produce a clear one-line error message.

---

## 9. Future Enhancements (Not required for v1)

* Project upgrade commands when schema versions change
* Interactive CLI mode
* Colorized terminal output
* Parallel staleness checking
* Batch import of links from CSV

---

[Back to Overview](kleuw_overall_spec.md)
