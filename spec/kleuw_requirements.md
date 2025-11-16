# Kleuw Requirements Specification

[Back to Overview](kleuw_overall_spec.md)

## 1. Purpose

This document defines the **functional** and **non-functional** requirements for the **Kleuw** project. These requirements guide all subsequent design, implementation, and testing.

## 2. Project Summary

Kleuw is a tool for:

* Capturing semantic relationships between files
* Optionally referencing specific line ranges
* Detecting when linked regions become stale due to file changes
* Providing a simple GUI for browsing files, selecting line ranges, and creating/editing relationships
* Providing a CLI for scripting and automation

The tool is intended as a foundation for future digital thread tooling.

## 3. Functional Requirements

### 3.1 Project File Management

* **FR-1:** Kleuw shall load and save a project JSON file that adheres to the Kleuw schema.
* **FR-2:** Kleuw shall support creating new empty project files.
* **FR-3:** Kleuw shall validate project files against baseline structural requirements.
* **FR-4:** The GUI shall track unsaved changes via a dirty indicator; persistence and close warnings are handled externally through the CLI or embedding application.

### 3.2 File Catalog

* **FR-5:** Users shall be able to add file paths to the project.
* **FR-6:** `kleuw add-file` shall verify that the referenced path exists and can optionally store a `sha256` hash when `--hash` is supplied.
* **FR-7:** Kleuw shall allow referencing a file by path or by a stable file identifier, automatically preferring `file_id` when a project entry matches the on-disk path.
* **FR-8:** If a file is missing or cannot be decoded, Kleuw shall report the corresponding links as stale.

Implementation note: The GUI's Files panel maintains its own ad-hoc list solely for opening files inside the viewers; callers must use the CLI or project helpers to persist file entries.

### 3.3 Relationship Creation

* **FR-9:** The GUI shall allow selecting two files and displaying them side-by-side.
* **FR-10:** The GUI shall allow selecting line ranges for each file.
* **FR-11:** The user shall be able to choose a relationship type from a fixed enumerated list.
* **FR-12:** Kleuw shall support whole-file relationships when no lines are selected.
* **FR-13:** Kleuw shall generate unique link IDs.
* **FR-14:** Kleuw shall compute and store region hashes for both sides of each link.

### 3.4 Relationship Viewing & Editing

* **FR-15:** The GUI shall display all links in a tabular list.
* **FR-16:** Selecting a link shall open its associated files and scroll to the appropriate region.
* **FR-17:** Users shall be able to edit link metadata (relationship type, notes, tags).
* **FR-18:** Users shall be able to recompute and overwrite region hashes via the CLI `recompute` command; the GUI exposes placeholders for this action but currently defers to the CLI.
* **FR-19:** Users shall be able to delete links.

### 3.5 Staleness Detection

* **FR-20:** Kleuw shall recompute region hashes and compare them with stored values.
* **FR-21:** Kleuw shall mark links as stale when region hashes do not match.
* **FR-22:** Staleness checks shall be accessible from both the GUI and the CLI.
* **FR-23:** Users shall be able to compute staleness for individual links or all links.

### 3.6 CLI Requirements

* **FR-24:** `kleuw init` shall create a new Kleuw project (and support `--force` when overwriting an existing file).
* **FR-25:** `kleuw add-file` shall register on-disk files, generate default `file-<n>` identifiers, and optionally compute hashes via `--hash`.
* **FR-26:** `kleuw list-files` and `kleuw list-links` shall render tabular output and, when `--json` is supplied, emit machine-readable payloads matching the schema.
* **FR-27:** `kleuw create-link` shall parse CLI region syntax, compute region hashes, attach `file_id` references when possible, and assign deterministic `link-<n>` identifiers.
* **FR-28:** `kleuw check` shall recompute region hashes for the selected links, surface human-readable and JSON diagnostics, and return exit code `1` whenever any link is stale. `list-links --stale-only` uses the same staleness evaluation pipeline.
* **FR-29:** `kleuw recompute` shall overwrite stored region hashes for the selected links after validating the project file.
* **FR-30:** `kleuw validate` shall read a project JSON file and report schema violations using `spec/kleuw.schema.json`.
* **FR-31:** `kleuw export` shall export files and annotated link staleness information in `json`, `csv`, or `txt` formats, each supporting the `--stale` filter.

## 4. Non-Functional Requirements (NFRs)

### 4.1 Usability

* **NFR-1:** GUI shall use clear layout and line-numbered views.
* **NFR-2:** Interface shall respond to selections within 200ms for typical file sizes (<5 MB).
* **NFR-3:** Users should be able to create a link in under 5 steps.

### 4.2 Performance

* **NFR-4:** Region hash computation should scale linearly with region size.
* **NFR-5:** Staleness check for a project with 500 links should complete within 3 seconds on mid‑range hardware.

### 4.3 Reliability

* **NFR-6:** All file operations shall handle missing files gracefully.
* **NFR-7:** JSON read/write operations must avoid data loss and preserve deterministic ordering.
* **NFR-8:** Undo/redo functionality is deferred; the current GUI surfaces state changes via the dirty indicator instead of maintaining an action stack.

### 4.4 Portability

* **NFR-9:** Kleuw shall run on Python 3.10+ using only the standard library.
* **NFR-10:** GUI shall be implemented using `tkinter` for portability across Windows, macOS, and Linux.

### 4.5 Maintainability

* **NFR-11:** Code shall be modular: separate modules for schema, hashing, staleness checking, CLI, GUI.
* **NFR-12:** Codebase shall include internal documentation referencing these specification files.

## 5. Constraints

* Use of Python standard library only (no third-party dependencies).
* File paths must remain portable and avoid OS-specific assumptions.
* JSON structure must conform to the official Kleuw schema.

## 6. Assumptions

* Users have basic familiarity with file systems and code editors.
* Project files are stored on a local file system.
* Files referenced in relationships are plain text.

## 7. Future Requirements (Non-binding for v1)

* Multi-span line selections
* External diff viewer integration
* Import/export to formats (GraphViz, CSV, XML)
* Plugin architecture
* Watch mode (real-time staleness detection)
* Syntax highlighting
* Undo/redo stack and project persistence directly from the GUI

---

[Back to Overview](kleuw_overall_spec.md)
