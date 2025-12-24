# AGENTS.md

This file defines the required behavior for **AI agents** contributing to the **Kleuw** project. Agents must follow these rules unless a human operator explicitly overrides them.

## Core Rules

* Follow all specifications in `spec/` before changing code or behavior.
* Do **not** add new runtime dependencies. Standard library only.
* Match existing patterns; avoid redesigns or architectural changes.
* Keep changes small, explicit, and fully typed.
* Run `make ci` to run all formatting, linting, typing, and testing checks before submitting work.

## Required Tools & Checks

All contributions must pass:

```
black --check src tests
isort --check-only src tests
ruff check src tests
mypy src
pytest --cov=kleuw --cov-fail-under=80
```

GUI tests (`pytest -m gui`) should run when relevant (under `xvfb-run` when available). If Tkinter cannot initialize (e.g., missing display), GUI tests should be skipped automatically.

## Code Expectations

* Prefer pure functions and simple, explicit logic.
* Keep GUI code minimal; place logic in non-GUI modules.
* Use dataclasses where appropriate.
* Avoid duplication; follow existing module patterns.
* All public functions must have complete type hints and Google-style docstrings.

## Tests

* Add tests for all new behavior.
* Add regression tests for bug fixes.
* Mirror module structure inside `tests/`.
* Do not reduce coverage or exclude code without instruction.

## Schema & Project Structure

* The authoritative schema is `spec/kleuw.schema.json`.
* Changes must align with the schema and specs.
* Do not modify the repository structure or schema unless instructed.

## CLI Consistency

When editing `cli.py`:

* Follow Unix-style conventions.
* Preserve flag names, command shapes, and `--json` output.
* Return proper exit codes (`0` = success, `1` = failure).

## Documentation

Whenever behavior changes:

* Update related specs in `spec/`.
* Keep comments concise and helpful.
* Avoid large narrative blocks.

## Git / Contribution Style

Contributions should resemble clean, minimal PRs:

* Small scope
* Clear commit-style summaries
* Conventional commit prefixes (`feat:`, `fix:`, etc.)
* All checks passing


## Task System Rules

Tasks live in `tasks/tasks.json`.

Agents must:

* Modify **only** the task assigned.
* Change **only the `status` field** when marking it complete.
* Use one of: `to do`, `complete`, `won't do`.
* Mark complete **only** when all acceptance criteria and referenced specs are satisfied.

No opportunistic refactors, no changes to other tasks, and no spec updates unless directed.


## Before Modifying Anything

Agents must:

1. Read the relevant specs.
2. Review related modules.
3. Identify any required updates to tests, docs, CLI, or schema.
4. Run all checks.
5. Keep changes narrowly focused.

If unsure, stop and request clarification.

## Summary Checklist

An agent’s output must:

* Conform to all specs and schema
* Use standard library only
* Pass formatting, linting, typing, tests, and coverage
* Include or update tests
* Maintain project structure
* Document behavior changes

All must be satisfied **before** presenting output.
