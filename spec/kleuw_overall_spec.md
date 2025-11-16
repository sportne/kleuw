# Kleuw Project Specification (Overview)

This is the **entry point** for all specification documents for the Kleuw project. Kleuw is a tool for capturing, managing, and validating semantic relationships between files — including line-level links — and detecting staleness when linked regions change.

## Document Structure

The Kleuw specification is organized into several sub-documents, each covering one major portion of the system:

* [Requirements](kleuw_requirements.md)
* [Data Format Schema](kleuw_schema.md)
* [UI Design Specification](kleuw_ui.md)
* [CLI Specification](kleuw_cli.md)
* [Hashing & Staleness Specification](kleuw_staleness.md)

Each sub-document links back to this overview.

## Implementation Snapshot

The initial implementation adheres to the following structure:

* **CLI (`src/kleuw/cli.py`)** – Provides `init`, `add-file`, `list-files`, `create-link`,
  `list-links`, `check`, `recompute`, `validate`, and `export` commands. The CLI is the
  entry point for persistence and for schema validation (`spec/kleuw.schema.json`).
* **GUI (`src/kleuw/gui.py`)** – Presents a Tkinter application centered on the link
  workspace. It loads text files into left/right viewers, allows full-line selections,
  creates or edits links within an in-memory `Project`, and performs staleness checks by
  calling the same core logic as the CLI.
* **Shared core modules** – `model.py`, `project.py`, `hashing.py`, `staleness.py`, and
  `io.py` implement the schema-defined data structures, region hashing, validation, and
  JSON IO routines used by both front ends.

All behavioral specifics referenced by the code live in the subordinate spec documents
listed above; this file simply ties them together and documents the state of the shipped
implementation.

## Purpose

The purpose of this documentation set is to guide the future implementation of Kleuw in a stable, structured, and version-controlled manner.

## Versioning

* **Spec Version:** 0.1 (Draft)
* **Kleuw Schema Version:** 1

## Next Steps

Continue reading the linked sub-documents for detailed requirements and design guidance.
