# Kleuw

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](LICENSE)
![Build Status](https://img.shields.io/badge/build-make%20ci%20passing-4c1?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-80.3%25-yellowgreen?style=flat-square)
![Static Analysis](https://img.shields.io/badge/static%20analysis-ruff%20%2B%20mypy%20clean-4c1?style=flat-square)

Kleuw is a tool for capturing, managing, and validating semantic relationships between files — including line‑level links — and detecting staleness when linked regions change.

This project offers both a **CLI** and a **Tkinter‑based GUI** for inspecting files side‑by‑side, selecting line ranges, and defining typed relationships.

Kleuw is built with reliability, clarity, and reproducibility in mind.
Runtime dependencies are restricted to the Python standard library.

---

# Getting Started

## Installation (Development Mode)

To install Kleuw along with all development tools:

```bash
make install-dev
```

This installs:

* black (formatting)
* isort (import ordering)
* ruff (linting)
* mypy (type checking)
* pytest + pytest-cov (testing & coverage)

All tool configuration lives in **pyproject.toml**.

## Installation (Runtime Only)

If you want to install Kleuw without development tools:

```bash
pip install -e .
```

---

# Project Structure

```
kleuw/
├── README.md                # This file
├── CONTRIBUTING.md          # Guidelines for human contributors
├── AGENTS.md                # Guidelines for AI/automated contributors
├── pyproject.toml           # Tooling + packaging config
├── Makefile                 # Unified developer workflow
├── spec/                    # Authoritative project specification
│   ├── kleuw_overall_spec.md
│   ├── kleuw_requirements.md
│   ├── kleuw_schema.md
│   ├── kleuw_ui.md
│   ├── kleuw_cli.md
│   ├── kleuw_staleness.md
│   └── kleuw.schema.json
├── src/kleuw/               # Main Python package
├── tests/                   # Unit and GUI tests
└── examples/                # Reference project files
```

---

# Usage

Detailed CLI and GUI specifications live in the `spec/` directory.

## CLI

Kleuw ships with a fully functional CLI entry point named `kleuw`. The
implemented subcommands mirror `src/kleuw/cli.py`:

* `init` – create a new JSON project file (`--force` overwrites)
* `add-file` – register a file path and optionally compute its hash
* `list-files` – display tracked files in a table or via `--json`
* `create-link` – create a link by passing `--src`, `--dst`, `--type`, `--note`, and `--tags`
* `list-links` – list links, with `--json`, `--stale-only`, and `--type` filters
* `check` – recompute region hashes, flag stale links, and set exit codes accordingly
* `recompute` – persist freshly computed region hashes for the selected links
* `validate` – validate a project against `spec/kleuw.schema.json`
* `export` – emit JSON/CSV/text summaries (and optionally `--stale`-only data)

Reporting commands accept `--json` where applicable so that automation can
consume the exact structures defined by the Kleuw schema.

Design: **spec/kleuw_cli.md**

## GUI

The Tkinter GUI focuses on visualizing files, selecting regions, creating or
editing links, and reviewing staleness. Implemented behaviors include:

* Loading arbitrary text files into independent left/right viewers from the Files panel
* Line-locked selections with synchronized status-bar summaries
* Manual relationship creation once both viewers contain files and a relationship type
* Editing and deleting existing links plus double-click navigation that loads the linked regions
* Running a project-wide staleness check (with highlighting and filtering) using the same logic as the CLI

Menu and toolbar entries other than “Create Link” and “Check Staleness” currently
display placeholder dialogs; persistence is handled through the CLI or external
tooling.

Design: **spec/kleuw_ui.md**

---

# Development

If you plan to contribute to the project, *please read:*

* **CONTRIBUTING.md** (human workflow)
* **AGENTS.md** (AI/automated workflow)

### Running All Checks

To run the full suite of checks locally:

```bash
make ci
```

This includes formatting checks, linting, type checking, unit tests, coverage, and GUI tests.

### Individual Tasks

You can also run phases individually:

```bash
make format
make format-check
make lint
make typecheck
make test
make coverage
make gui-test
```

---

# Specifications

**All architectural and behavioral details are defined in the** `spec/` **directory.**
These documents are the authoritative reference for:

* Data format and JSON schema
* Staleness and hashing rules
* CLI and GUI behavior
* Requirements and design decisions

If you change any behavior, update the relevant spec files.

---

# Additional Resources

* **CONTRIBUTING.md** — Human workflow and development requirements
* **AGENTS.md** — Automation/AI contributor rules
* **spec/** — Deep technical design docs

Kleuw is designed for clarity, reproducibility, and long‑term maintainability.
Thank you for helping us build it!
