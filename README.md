# Kleuw

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

The CLI will support:

* Initializing a project
* Adding and listing files
* Creating links between files and line ranges
* Detecting stale relationships

Design: **spec/kleuw_cli.md**

## GUI

The GUI provides an interface for:

* Side‑by‑side file viewing
* Line‑range selection
* Choosing a typed relationship
* Reviewing and editing existing links

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
