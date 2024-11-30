SHELL := /bin/bash
# =============================================================================
# Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
NODE_MODULES_EXISTS		=	$(shell python3 -c "if __import__('pathlib').Path('node_modules').exists(): print('yes')")

.EXPORT_ALL_VARIABLES:

ifndef VERBOSE
.SILENT:
endif


.PHONY: help
help: 		   										## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: upgrade
upgrade:       										## Upgrade all dependencies to the latest stable versions
	@echo "=> Updating all dependencies"
	@npm upgrade --latest
	@echo "=> Dependencies Updated"
	# @pre-commit autoupdate
	# @echo "=> Updated Pre-commit"

# =============================================================================
# Developer Utils
# =============================================================================
install:											## Install the project and
	@if [ "$(NODE_MODULES_EXISTS)" ]; then echo "=> Removing existing node modules"; fi
	@if [ "$(NODE_MODULES_EXISTS)" ]; then $(MAKE) destroy-node_modules; fi
	@echo "=> Installing all dependencies"
	@npm ci install --silent
	@echo "=> Install complete! Note: If you want to re-install re-run 'make install'"

destroy-node_modules: 											## Destroy the node environment
	@rm -rf node_modules
# =============================================================================
# Tests, Linting, Coverage, Build
# =============================================================================
.PHONY: lint
lint: 												## Runs pre-commit hooks; includes ruff linting, codespell, black
	@echo "=> Running pre-commit process"
	@pre-commit run --all-files
	@echo "=> Pre-commit complete"

.PHONY: test
test:  												## Run the tests
	@echo "=> Running test cases"
	@npm run test
	@echo "=> Tests complete"

.PHONY: build
build:
	@echo "=> Building package..."
	@npm run build
	@echo "=> Package build complete..."

.PHONY: publish
publish: test build
	@echo "=> Publishing package..."
	@npm publish
	@echo "=> Package publish complete..."
