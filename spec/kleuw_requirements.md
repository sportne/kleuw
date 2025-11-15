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
* **FR-4:** Kleuw shall track unsaved changes and warn the user when closing with unsaved modifications.

### 3.2 File Catalog

* **FR-5:** Users shall be able to add file paths to the project.
* **FR-6:** Kleuw shall compute and store optional file-level hashes.
* **FR-7:** Kleuw shall allow referencing a file by path or by a stable file identifier.
* **FR-8:** If a file is missing, Kleuw shall report the corresponding links as stale.

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
* **FR-18:** Users shall be able to recompute and overwrite region hashes.
* **FR-19:** Users shall be able to delete links.

### 3.5 Staleness Detection

* **FR-20:** Kleuw shall recompute region hashes and compare them with stored values.
* **FR-21:** Kleuw shall mark links as stale when region hashes do not match.
* **FR-22:** Staleness checks shall be accessible from both the GUI and the CLI.
* **FR-23:** Users shall be able to compute staleness for individual links or all links.

### 3.6 CLI Requirements

* **FR-24:** Kleuw shall provide an `init` command for creating new project files.
* **FR-25:** Kleuw shall provide a `add-file` command for registering files.
* **FR-26:** Kleuw shall allow creating links via command-line parameters.
* **FR-27:** The CLI shall support staleness checking and printing results.
* **FR-28:** The CLI shall support exporting summaries in text or JSON.

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
* **NFR-8:** Undo/redo stack shall support at least 20 actions.

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

---

[Back to Overview](kleuw_overall_spec.md)
