# Contributing to Kleuw

Thank you for your interest in contributing to **Kleuw**! This guide is for **human contributors**. If you're an automated agent, please refer instead to **AGENTS.md**, which contains strict rules tailored for automated workflows.

Kleuw is designed for clarity, consistency, and reliability. This document explains how to set up your development environment, submit contributions, and follow the project's standards.

---

# 1. Code of Conduct

Be respectful, constructive, and patient. All contributors should share an interest in building high‑quality, maintainable software.

---

# 2. Development Environment Setup

1. Clone the repository:

   ```bash
   git clone <repo-url>
   cd kleuw
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
   ```

3. Install the project in editable mode with development dependencies:

   ```bash
   make install-dev
   ```

This installs:

* black (formatter)
* isort (import organizer)
* ruff (linter)
* mypy (type checker)
* pytest + pytest-cov (tests & coverage)

All tooling is configured in `pyproject.toml`.

---

# 3. Project Structure Overview

```
kleuw/
├── README.md
├── CONTRIBUTING.md
├── AGENTS.md
├── spec/                # Project specification documents
├── src/kleuw/           # Main Python package
├── tests/               # Unit and GUI tests
├── examples/            # Example project files
└── Makefile             # Developer convenience tasks
```

Specification documents in `spec/` are the authoritative reference for the data model, staleness system, UI, CLI, and JSON schema.

---

# 4. Workflow for Contributions

## 4.1 Create a Feature Branch

Use descriptive branch names such as:

* `feature/add-staleness-report`
* `fix/hash-mismatch-bug`

## 4.2 Make Your Changes

Follow these rules:

* Keep changes **focused and small**.
* Update or add tests for any new feature or bug fix.
* Update relevant documentation in `spec/` when behavior changes.
* Ensure code is readable, typed, and well‑commented.

## 4.3 Run All Quality Checks

Before submitting any changes, run:

```bash
make format
make lint
make typecheck
make coverage
```

You should see **no errors**, and coverage must be **≥ 80%**.

GUI tests (Tkinter) may be run via:

```bash
make gui-test
```

They may skip automatically if Tk cannot initialize.

---

# 5. Submitting Your Contribution

1. Commit your changes using clear, imperative messages:

   * `fix: correct region hash computation`
   * `feat: add schema validation CLI command`
   * `docs: update schema spec`

2. Push your branch and open a Pull Request (PR).

3. In the PR description, include:

   * A summary of the change
   * Motivation and context
   * Links to any updated spec documents
   * Notes on testing

4. Ensure CI is passing (GitHub Actions).

Reviews will focus on correctness, clarity, adherence to design, and alignment with project standards.

---

# 6. Testing Guidelines

* Tests should mirror the structure of the source tree.
* For every bug fix, include a **regression test**.
* For new features, include tests covering:

  * Expected behavior
  * Error handling
  * Edge cases
* Avoid testing UI layout; instead test GUI **flows and logic**.

---

# 7. Documentation Expectations

If your change:

* Adds a feature → update or create a spec document
* Modifies CLI behavior → update `kleuw_cli.md`
* Modifies data format → update `kleuw_schema.md` + JSON schema
* Changes staleness behavior → update `kleuw_staleness.md`

Additionally:

* Use Markdown formatting
* Keep conceptual documentation in `spec/`
* Keep user-focused documentation in `README.md`

These specification files describe the **current implementation**, not just the
intended design. Please keep them synchronized with any code changes so the CLI,
GUI, and documentation remain aligned.

---

# 8. Project Standards Summary

You must follow:

* Formatting: **black**, isort (black profile)
* Linting: **ruff**
* Types: **mypy**
* Testing: **pytest**, coverage ≥ 80%
* No new runtime dependencies outside the Python standard library
* Edit only one focused area at a time
* Update documentation when behavior changes
* Keep a clean and readable Git history

---

# 9. Need Help?

If you're uncertain whether a change aligns with the specification or project norms:

* Check the `spec/` folder
* Read AGENTS.md for more rules
* Open an Issue asking for design guidance
* Keep PRs small and propose incremental improvements

We appreciate your contributions!
