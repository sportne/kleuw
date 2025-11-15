# Makefile for Kleuw

PYTHON      ?= python
SRC_DIR     := src
TEST_DIR    := tests
PACKAGE     := kleuw

.PHONY: \
    help install-dev \
    format format-check \
    lint typecheck \
    test coverage gui-test \
    ci

help:
	@echo "Kleuw Makefile targets:"
	@echo "  make install-dev   - Install project with dev dependencies"
	@echo "  make format        - Run black and isort (auto-format)"
	@echo "  make format-check  - Check formatting (no changes made)"
	@echo "  make lint          - Run ruff linting"
	@echo "  make typecheck     - Run mypy static type checking"
	@echo "  make test          - Run unit tests"
	@echo "  make coverage      - Run unit tests with coverage threshold"
	@echo "  make gui-test      - Run GUI-marked tests"
	@echo "  make ci            - Run all phase checks (convenience target)"

install-dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

# ----- Formatting -----

format:
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)

format-check:
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort --check-only $(SRC_DIR) $(TEST_DIR)

# ----- Linting / Static Analysis -----

lint:
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)

typecheck:
	$(PYTHON) -m mypy $(SRC_DIR)

# ----- Testing -----

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-fail-under=80

gui-test:
	$(PYTHON) -m pytest -m gui

# ----- Convenience Target -----

ci: format-check lint typecheck test coverage gui-test
