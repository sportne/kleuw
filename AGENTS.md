# AGENTS.md

This document provides guidance for **AI agents** and **automated contributions** to the **Kleuw** project.
It defines what you *must* follow when writing, modifying, or reviewing code, documentation, or project assets.

AI agents should treat this file as the authoritative source for development norms.

---

# 1. Core Principles

* **Respect the spec**: Before modifying code, consult the design documents in `spec/`.
* **No new runtime dependencies**: Kleuw must run on Python's standard library only.
* **Be conservative**: Match existing patterns; avoid clever or novel approaches.
* **Be explicit**: Use readable code, docstrings, and type hints.
* **Keep changes small**: Minimize risk; isolate changes; include tests.
* **Run all checks**: Before proposing modifications, ensure all quality gates pass.

---

# 2. Project Structure Awareness

AI agents must understand the repository layout:

```
kleuw/
├── README.md
├── AGENTS.md
├── spec/
│   ├── kleuw_overall_spec.md
│   ├── kleuw_requirements.md
│   ├── kleuw_schema.md
│   ├── kleuw_ui.md
│   ├── kleuw_cli.md
│   ├── kleuw_staleness.md
│   └── kleuw.schema.json
├── src/
│   └── kleuw/
│       ├── __init__.py
│       ├── cli.py
│       ├── gui.py
│       ├── model.py
│       ├── schema.py
│       ├── hashing.py
│       ├── staleness.py
│       ├── io.py
│       ├── project.py
│       └── utils.py
├── tests/
└── examples/
```

Changes must respect this structure.

---

# 3. Code Formatting Rules

Use **Black** for all Python code.

* Line length: **88** (default)
* Target version: Python 3.10+
* Run:

  ```bash
  black src tests
  ```
* PR/agent submissions must pass:

  ```bash
  black --check src tests
  ```

Imports must be sorted with **isort** using Black’s profile:

```bash
isort src tests
isort --check-only src tests
```

---

# 4. Linting & Static Analysis

Use **ruff** for linting:

```bash
ruff check src tests
```

Use **mypy** for static type checking:

```bash
mypy src
```

Type-checking expectations:

* All new public functions must include type hints.
* Do not introduce `Any` unless required.
* Use `cast()` and `# type: ignore` sparingly.

---

# 5. Unit Testing Standards

All non-GUI logic must be covered by **pytest** tests.

* Tests go in `tests/` and mirror structure of `src/kleuw/`.
* Test file naming: `test_*.py` only.
* Use pytest’s style (functions > classes unless needed).
* New features must include tests.
* Fixing a bug **requires** a regression test.

Run all tests via:

```bash
pytest
```

---

# 6. GUI / Tkinter Testing

GUI code must remain minimal and thin; most logic belongs in testable modules.

Headless GUI tests:

* Use `pytest -m gui` for GUI tests.
* Tests should:

  * Instantiate a minimal `Tk()` root
  * Exercise core workflows (load, open files, create link)
  * Avoid relying on screen dimensions or real displays
* On CI, run under `xvfb-run` when available.

If Tkinter cannot initialize (e.g., missing display), GUI tests should skip automatically.

---

# 7. Code Coverage Requirements

Coverage is collected via:

```bash
pytest --cov=kleuw --cov-report=term-missing
```

Coverage thresholds:

* **80% minimum** (hard fail)
* **95% target** (soft goal, encouraged)

Do not exclude code from coverage unless strictly necessary (e.g., `__main__` or Tk bootstrap).

---

# 8. JSON Schema Enforcement

The file `spec/kleuw.schema.json` is the authoritative schema.

Agents must:

* Validate any changed project JSON files against this schema.
* Align code changes with schema expectations.
* Not modify the schema unless the design has changed.

If modifying the schema:

* Update related docs in `spec/`.
* Increment schema version if a breaking change is introduced.

---

# 9. Documentation & Comments

AI agents must:

* Update Markdown specs (`spec/*.md`) when modifying behavior.
* Maintain consistent, clear docstrings using **Google-style**.
* Use inline comments sparingly, only where clarity is needed.

Do **not** generate large blocks of inline commentary.

---

# 10. Dependency Rules

Runtime dependencies:

* **Standard Library Only** — no external packages.

Dev dependencies (allowed):

* `black`, `isort`, `ruff`, `mypy`, `pytest`, `pytest-cov`

Agents must not add non-stdlib runtime imports.

---

# 11. CLI Design Consistency

When modifying CLI (`src/kleuw/cli.py`):

* Follow Unix-style commands and conventions.
* Preserve existing command patterns.
* Ensure `--json` output remains stable and machine-readable.
* Exit codes must remain meaningful:

  * `0` success
  * `1` general failure or staleness detection

---

# 12. Git Workflow Rules

AI agents should structure contributions as if preparing a PR:

* Use small, isolated changes.
* Write clear, imperative commit messages.
* Prefer conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
* Ensure all tests and checks pass before submitting.

---

# 13. Continuous Integration Expectations

All submissions must pass:

1. `black --check`
2. `isort --check-only`
3. `ruff check`
4. `mypy src`
5. `pytest --cov=kleuw --cov-fail-under=80`
6. `pytest -m gui` (if display is available)

Agents should assume CI will block contributions if any of the above fail.

---

# 14. Before Modifying Any File, Agents Must:

1. **Read** relevant specs in `spec/`.
2. **Check** whether change impacts UI, CLI, schema, docs, or tests.
3. **Search** for existing patterns in the code and follow them.
4. **Run** all lint, static-type, test, and coverage tools.
5. **Update** documentation if behavior changes.
6. **Include** or update tests.
7. **Minimize** scope of modifications.

---

# 15. When Creating New Code

* Prefer pure functions when possible.
* Keep GUI code minimal; logic goes into core modules.
* Use descriptive variable names; avoid single-letter names except for loops.
* Use dataclasses or typed dicts appropriately.
* Do not duplicate logic; refactor instead.

---

# 16. Summary for AI Agents

When contributing code, you must:

* **Conform to the specs**
* **Honor the schema**
* **Format with black**
* **Pass ruff, mypy, pytest**
* **Meet coverage thresholds**
* **Avoid new runtime dependencies**
* **Document behavior changes**
* **Write or update tests**

This checklist must be followed **before** suggesting or submitting any code changes.

---

# 17. Final Note

AI agents are expected to behave as careful, professional contributors.
If uncertain, prefer:

* Minimal changes
* Explicit reasoning in PR summaries
* Alignment with existing design documents

When in doubt: **consult `/spec` first.**

---
