# Makefile for pub-search-kit - Python publication search toolkit

PROJECT_NAME = pub-search-kit
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
SRC = src
TESTS = tests

# Colors
GREEN=\033[0;32m
CYAN=\033[0;36m
YELLOW=\033[1;33m
NC=\033[0m

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "$(CYAN)$(PROJECT_NAME) developer commands$(NC)"
	@echo
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: setup
setup: venv install-deps ## Create venv and install development dependencies

.PHONY: venv
venv: ## Create Python virtual environment (if missing)
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
		$(PIP) install --upgrade pip; \
	fi

.PHONY: install-deps
install-deps: venv ## Install project dependencies (dev extras)
	@$(PIP) install --upgrade pip
	@$(PIP) install -e .[dev]
	@$(PIP) install build

.PHONY: install
install: venv ## Install package in editable mode (runtime deps only)
	@$(PIP) install -e .

.PHONY: test
test: setup ## Run pytest suite
	@$(PYTHON) -m pytest $(TESTS) -v

.PHONY: build
build: setup ## Build source and wheel distributions
	@$(PYTHON) -m build

.PHONY: format
format: setup ## Format code with black
	@$(PIP) install black
	@$(PYTHON) -m black $(SRC) $(TESTS)

.PHONY: lint
lint: setup ## Run ruff lint checks
	@$(PIP) install ruff
	@$(PYTHON) -m ruff check $(SRC) $(TESTS)

.PHONY: release
release: ## Tag version from pyproject.toml and push main + tag
	@VERSION=$$(python3 - <<'PY'
import pathlib, re
text = pathlib.Path('pyproject.toml').read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
print(match.group(1) if match else '')
PY
); \
	if [ -z "$$VERSION" ]; then \
		echo "Unable to parse version from pyproject.toml"; \
		exit 1; \
	fi; \
	echo "Tagging release v$$VERSION"; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	git push origin main; \
	git push origin "v$$VERSION"

.PHONY: clean
clean: ## Remove build artifacts and caches
	@rm -rf build dist *.egg-info htmlcov .pytest_cache .mypy_cache
	@find $(SRC) $(TESTS) -type d -name '__pycache__' -exec rm -rf {} +

.PHONY: clean-venv
clean-venv: ## Remove virtual environment
	@rm -rf $(VENV_DIR)
