SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# =============================================================================
# Configuration and Environment Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# -----------------------------------------------------------------------------
# Display Formatting and Colors
# -----------------------------------------------------------------------------
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")
ERROR := $(shell printf "$(RED)✖$(NC)")
NODEENV ?= 0
EXTRAS ?=
UV_SYNC_EXTRAS := $(foreach extra,$(EXTRAS),--extra $(extra))

# =============================================================================
# Help and Documentation
# =============================================================================

.PHONY: help
help:                                               ## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# =============================================================================
# Installation and Environment Setup
# =============================================================================

.PHONY: install-uv
install-uv:                                         ## Install latest version of uv
	@echo "${INFO} Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully"

.PHONY: install
install: destroy clean                              ## Install the project, dependencies, and pre-commit
	@echo "${INFO} Starting fresh installation..."
	@uv venv >/dev/null 2>&1
	@uv sync --dev $(UV_SYNC_EXTRAS)
	@if [ "$(NODEENV)" = "1" ]; then \
		echo "${INFO} Installing Node environment via nodeenv... 📦"; \
		uvx nodeenv .venv --force --quiet >/dev/null 2>&1; \
	elif ! command -v npm >/dev/null 2>&1; then \
		echo "${WARN} npm not found. Re-run with NODEENV=1 to provision nodeenv or install Node.js manually."; \
		exit 1; \
	fi
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm install --no-fund
	@echo "${OK} Installation complete! 🎉"

.PHONY: destroy
destroy:                                            ## Destroy the virtual environment
	@echo "${INFO} Destroying virtual environment... 🗑️"
	@uv run pre-commit clean >/dev/null 2>&1
	@rm -rf .venv
	@echo "${OK} Virtual environment destroyed 🗑️"

# =============================================================================
# Dependency Management
# =============================================================================

.PHONY: upgrade
upgrade:                                            ## Upgrade all dependencies to latest stable versions
	@echo "${INFO} Updating all dependencies... 🔄"
	@uv lock --upgrade
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm update --no-fund
	@echo "${OK} Dependencies updated 🔄"
	@uv run pre-commit autoupdate
	@echo "${OK} Updated Pre-commit hooks 🔄"

.PHONY: lock
lock:                                              ## Rebuild lockfiles from scratch
	@echo "${INFO} Rebuilding lockfiles... 🔄"
	@uv lock --upgrade >/dev/null 2>&1
	@echo "${OK} Lockfiles updated"

# =============================================================================
# Build and Release
# =============================================================================

.PHONY: build
build:                                             ## Build the package
	@echo "${INFO} Building package... 📦"
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm install --no-fund --quiet
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm run build --quiet
	@uv build -o dist/py >/dev/null 2>&1
	@echo "${OK} Package build complete"

.PHONY: release
release:                                           ## Bump version and create release tag (bump=major|minor|patch)
	@echo "${INFO} Preparing for release... 📦"
	@make docs
	@make clean
	@make build
	@uv run bump-my-version bump $(bump)
	@uv lock --upgrade-package litestar-vite >/dev/null 2>&1
	@echo "${OK} Release complete 🎉"

.PHONY: pre-release
pre-release:                                       ## Start a pre-release: make pre-release version=0.15.0-alpha.1
	@if [ -z "$(version)" ]; then \
		echo "${ERROR} Usage: make pre-release version=X.Y.Z-alpha.N"; \
		echo ""; \
		echo "Pre-release workflow:"; \
		echo "  1. Start alpha:     make pre-release version=0.15.0-alpha.1"; \
		echo "  2. Next alpha:      make pre-release version=0.15.0-alpha.2"; \
		echo "  3. Move to beta:    make pre-release version=0.15.0-beta.1"; \
		echo "  4. Move to rc:      make pre-release version=0.15.0-rc.1"; \
		echo "  5. Final release:   make release bump=patch (from rc) OR bump=minor (from stable)"; \
		exit 1; \
	fi
	@echo "${INFO} Preparing pre-release $(version)... 🧪"
	@make clean
	@make build
	@uv run bump-my-version bump --new-version $(version) pre
	@uv lock --upgrade-package litestar-vite >/dev/null 2>&1
	@echo "${OK} Pre-release $(version) complete 🧪"
	@echo ""
	@echo "${INFO} Next steps:"
	@echo "  1. Push: git push origin HEAD"
	@echo "  2. Create a GitHub pre-release: gh release create v$(version) --prerelease --title 'v$(version)'"
	@echo "  3. This will publish to PyPI/npm with pre-release tags"

# =============================================================================
# Cleaning and Maintenance
# =============================================================================

.PHONY: clean
clean:                                              ## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory... 🧹"
	@rm -rf pytest_cache .ruff_cache .hypothesis build/ -rf dist/ .eggs/ .coverage coverage.xml coverage.json htmlcov/ .pytest_cache tests/.pytest_cache tests/**/.pytest_cache .mypy_cache .unasyncd_cache/ .auto_pytabs_cache node_modules docs-build coverage >/dev/null 2>&1
	@rm -f .litestar*.json >/dev/null 2>&1 || true
	@find . -name '*.egg-info' -exec rm -rf {} + >/dev/null 2>&1
	@find . -type f -name '*.egg' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*.pyc' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*.pyo' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*~' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '__pycache__' -exec rm -rf {} + >/dev/null 2>&1
	@find . -name '.ipynb_checkpoints' -exec rm -rf {} + >/dev/null 2>&1
	@echo "${OK} Working directory cleaned"
	$(MAKE) clean-examples
	$(MAKE) docs-clean

.PHONY: clean-examples
clean-examples:                                     ## Clean all example build artifacts
	@echo "${INFO} Cleaning example artifacts... 🧹"
	@find examples -maxdepth 2 -type d -name "node_modules" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name "public" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name ".vite" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name ".angular" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name ".nuxt" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name ".output" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type d -name ".svelte-kit" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 3 -type d -name "generated" -exec rm -rf {} + >/dev/null 2>&1 || true
	@find examples -maxdepth 2 -type f -name ".litestar*.json" -exec rm -f {} + >/dev/null 2>&1 || true
	@echo "${OK} Example artifacts cleaned"

# =============================================================================
# Testing and Quality Checks
# =============================================================================

.PHONY: test
test:                                              ## Run the tests
	@echo "${INFO} Running test cases... 🧪"
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" npm run test
	@uv run pytest -n 2 --quiet
	@echo "${OK} Tests passed ✨"

.PHONY: coverage
coverage:                                          ## Run tests with coverage report
	@echo "${INFO} Running tests with coverage... 📊"
	@uv run pytest --cov=src/py/litestar_vite -n 2 --quiet
	@uv run coverage html >/dev/null 2>&1
	@uv run coverage xml >/dev/null 2>&1
	@echo "${OK} Coverage report generated ✨"

# -----------------------------------------------------------------------------
# Type Checking
# -----------------------------------------------------------------------------

.PHONY: mypy
mypy:                                              ## Run mypy
	@echo "${INFO} Running mypy... 🔍"
	@uv run dmypy run
	@echo "${OK} Mypy checks passed ✨"

.PHONY: mypy-nocache
mypy-nocache:                                      ## Run Mypy without cache
	@echo "${INFO} Running mypy without cache... 🔍"
	@uv run mypy
	@echo "${OK} Mypy checks passed ✨"

.PHONY: pyright
pyright:                                           ## Run pyright
	@echo "${INFO} Running pyright... 🔍"
	@uv run pyright
	@echo "${OK} Pyright checks passed ✨"

.PHONY: basedpyright
basedpyright:                                      ## Run basedpyright
	@echo "${INFO} Running basedpyright... 🔍"
	@uv run basedpyright
	@echo "${OK} Basedpyright checks passed ✨"

.PHONY: type-check
type-check: mypy pyright                           ## Run all type checking

# -----------------------------------------------------------------------------
# Linting and Formatting
# -----------------------------------------------------------------------------

.PHONY: pre-commit
pre-commit:                                        ## Run pre-commit hooks
	@echo "${INFO} Running pre-commit checks... 🔎"
	@NODE_OPTIONS="--no-deprecation --disable-warning=ExperimentalWarning" uv run pre-commit run --color=never --all-files
	@echo "${OK} Pre-commit checks passed ✨"

.PHONY: slotscheck
slotscheck:                                        ## Run slotscheck
	@echo "${INFO} Running slots check... 🔍"
	@uv run slotscheck -m litestar_vite
	@echo "${OK} Slots check passed ✨"

.PHONY: fix
fix:                                               ## Run code formatters
	@echo "${INFO} Running code formatters... 🔧"
	@uv run ruff check --fix --unsafe-fixes
	@echo "${OK} Code formatting complete ✨"

.PHONY: lint
lint: pre-commit type-check slotscheck             ## Run all linting checks

.PHONY: check-all
check-all: lint test coverage                      ## Run all checks (lint, test, coverage)

# =============================================================================
# Documentation
# =============================================================================

.PHONY: docs-clean
docs-clean:                                        ## Clean documentation build
	@echo "${INFO} Cleaning documentation build assets... 🧹"
	@rm -rf docs/_build >/dev/null 2>&1
	@echo "${OK} Documentation assets cleaned"

.PHONY: docs-serve
docs-serve: docs-clean                             ## Serve documentation locally
	@echo "${INFO} Starting documentation server... 📚"
	@uv run sphinx-autobuild docs docs/_build/ -j auto --watch src/py/litestar_vite --watch docs --watch CONTRIBUTING.rst --port 8002

.PHONY: docs
docs: docs-clean                                   ## Build documentation
	@echo "${INFO} Building documentation... 📝"
	@uv run sphinx-build -M html docs docs/_build/ -E -a -j auto -W --keep-going
	@echo "${OK} Documentation built successfully"

.PHONY: docs-linkcheck
docs-linkcheck:                                    ## Check documentation links
	@echo "${INFO} Checking documentation links... 🔗"
	@uv run sphinx-build -b linkcheck ./docs ./docs/_build -D linkcheck_ignore='http://.*','https://.*'
	@echo "${OK} Link check complete"

.PHONY: docs-linkcheck-full
docs-linkcheck-full:                               ## Run full documentation link check
	@echo "${INFO} Running full link check... 🔗"
	@uv run sphinx-build -b linkcheck ./docs ./docs/_build -D linkcheck_anchors=0
	@echo "${OK} Full link check complete"

.PHONY: docs-demos
docs-demos:                                        ## Generate demo GIFs locally (requires vhs)
	@echo "${INFO} Generating demo GIFs... 🎬"
	@command -v vhs >/dev/null 2>&1 || { echo "${ERROR} VHS required. Install with: brew install vhs (macOS) or see https://github.com/charmbracelet/vhs"; exit 1; }
	@mkdir -p docs/_static/demos
	@for tape in docs/_tapes/*.tape; do \
		echo "${INFO} Processing $$tape..."; \
		VHS_NO_SANDBOX=true vhs "$$tape"; \
	done
	@echo "${OK} Demo GIFs generated successfully"

.PHONY: docs-all
docs-all: docs-demos docs                          ## Generate demos and build documentation

# =============================================================================
# Example Management
# =============================================================================

.PHONY: install-examples
install-examples:                                  ## Install dependencies for all examples
	@echo "${INFO} Installing example dependencies... 📦"
	@for dir in examples/*/; do \
		if [ -f "$${dir}package.json" ]; then \
			echo "${INFO} Installing $${dir}..."; \
			uv run litestar --app-dir "$${dir%/}" assets install || exit 1; \
		fi \
	done
	@echo "${OK} Example dependencies installed"

.PHONY: build-examples
build-examples:                                    ## Build all frontend examples
	@echo "${INFO} Building all examples... 📦"
	@for dir in examples/*/; do \
		if [ -f "$${dir}package.json" ]; then \
			echo "${INFO} Building $${dir}..."; \
			uv run litestar --app-dir "$${dir%/}" assets build || exit 1; \
		fi \
	done
	@echo "${OK} All examples built successfully"

.PHONY: test-examples
test-examples: build-examples                      ## Build and test all examples
	@echo "${INFO} Testing examples... 🧪"
	@uv run pytest src/py/tests/integration/test_examples.py -v
	@echo "${OK} Example tests passed"

.PHONY: test-examples-e2e
test-examples-e2e:                                 ## Run end-to-end example suite
	@echo "${INFO} Running E2E example tests... 🧪"
	@uv run pytest -n auto -m e2e src/py/tests/e2e -v --maxfail=1
	@echo "${OK} E2E example tests passed"
