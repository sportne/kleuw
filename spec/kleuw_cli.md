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

* If `--id` omitted, Kleuw generates one.
* Validates file exists.
* Optionally computes file-level hash if `--hash` provided.

**Options:**

* `--id` — user-specified file ID
* `--hash` — compute file hash (sha256)

---

### 4.3 `list-files`

```
kleuw list-files <project.json>
```

Prints the list of files in table format.

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
* Generates unique link ID.
* Appends new link to project.

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

Lists all or filtered links.

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
* Prints tabular diagnostics.
* Returns exit code:

  * **0** if no stale links
  * **1** if one or more stale

**Options:**

* `--json` — output structured results

**Example Output:**

```
ID    TYPE       STATUS   DETAILS
L12   implements STALE    src changed
L13   tests      OK       
```

---

### 4.7 `recompute`

```
kleuw recompute <project.json> [--link-id LID...]
```

Updates stored region hashes to current file state.

**Use Case:** Accepting updated content as the new baseline.

---

### 4.8 `validate`

```
kleuw validate <project.json>
```

Checks:

* Structural schema conformity
* File references
* Line range validity

Exit codes:

* **0** valid
* **1** invalid

---

### 4.9 `export`

```
kleuw export <project.json> --format {json,csv,txt}
```

Exports:

* file list
* link list
* staleness report (optional flag)

**Options:**

* `--format` — output style
* `--stale` — export only stale links

---

## 5. CLI Pattern Rules

* All commands accept `--json` for machine-readable output when applicable.
* Flags should have both long (`--type`) and short (`-t`) versions when possible.
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

JSON keys shall match the Kleuw schema’s property names.

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
