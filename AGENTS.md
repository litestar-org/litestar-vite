# AI Agent Guidelines for litestar-vite

**Version**: 1.0
**Last Updated**: 2025-11-01

This document provides guidance for AI assistants when working with this repository. It serves as the primary entry point for understanding the project structure, development workflows, and coding standards.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Development Workflows](#development-workflows)
5. [Code Standards](#code-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation System](#documentation-system)
8. [Agent-Specific Workflows](#agent-specific-workflows)

---

## Project Overview

**litestar-vite** is a library that provides seamless integration between the [Litestar](https://litestar.dev/) Python web framework and the [Vite](https://vitejs.dev/) next-generation frontend tooling. It includes support for [Inertia.js](https://inertiajs.com/) to facilitate the creation of modern single-page applications (SPAs) with server-side routing.

The project consists of:

- **Core Library**: A Python library (`litestar_vite`) that provides the Litestar plugin, asset loading, and Inertia support.
- **JS Library**: A small TypeScript library (`src/js`) that provides helper functions for the frontend.
- **Examples**: A collection of example projects (`examples/`) demonstrating various use cases (basic, Inertia with Vue, etc.).

### Technology Stack

#### Backend (Python)

- **Language**: Python 3.8+
- **Framework**: Litestar
- **Testing**: pytest
- **Linting & Formatting**: Ruff
- **Type Checking**: MyPy

#### Frontend (TypeScript)

- **Language**: TypeScript
- **Build Tool**: Vite
- **Testing**: Vitest
- **Linting & Formatting**: Biome

---

## Quick Start

All development tasks are managed via the `Makefile`.

```bash
# Install all dependencies (Python and Node.js) and pre-commit hooks
make install

# Run the full test suite for both Python and JS
make test

# Run all linting and type-checking
make lint

# Auto-format all code
make fix

# Build the package for distribution
make build

# Clean all temporary files and build artifacts
make clean
```

### Important: Command Execution

This project uses `uv` for Python package management, but all common commands are wrapped in the `Makefile`. You should use `make` targets as the primary way to interact with the project.

---

## Project Structure

```
litestar-vite/
├── .gemini/                    # Gemini agent workflow system
│   ├── GEMINI.md              # Gemini-specific workflow documentation
│   └── commands/              # Custom slash commands (prd, implement, etc.)
├── specs/                      # Comprehensive project specifications
│   ├── guides/                # Living documentation and patterns
│   │   ├── architecture.md
│   │   ├── code-style.md
│   │   ├── development-workflow.md
│   │   └── testing.md
│   ├── active/                # Active development workspaces (gitignored)
│   └── archive/               # Archived completed work (gitignored)
├── src/
│   ├── py/litestar_vite/      # Core Python library source
│   │   ├── inertia/           # Inertia.js integration
│   │   └── templates/         # Jinja2 templates for scaffolding
│   └── js/                    # Core TypeScript library source
│       ├── src/
│       └── tests/
├── examples/                   # Example applications
│   ├── basic/
│   └── inertia/
├── tests/                      # Python test suite (for src/py)
│   ├── unit/
│   └── integration/
├── Makefile                    # Development automation
├── pyproject.toml              # Python project configuration (PEP 621)
└── package.json                # Node.js project configuration
```

---

## Development Workflows

### Standard Development Flow

1. **Understand the requirement** - Review existing code, examples, and documentation.
2. **Check `specs/guides/`** - Consult architectural patterns and code style.
3. **Write code** - Follow established patterns in `src/py` or `src/js`.
4. **Write tests** - Add corresponding tests in `src/py/tests` or `src/js/tests`.
5. **Run quality checks** - Use `make lint` and `make test` frequently.
6. **Update documentation** - Keep `specs/guides/` and docstrings in sync with code changes.

### For Python Backend

```bash
# 1. Make changes to src/py/litestar_vite/
# 2. Run tests for the specific module
pytest src/py/tests/unit/test_your_module.py -v

# 3. Run linting and type-checking
make lint

# 4. Auto-fix formatting issues
make fix

# 5. Run all checks before committing
make check-all
```

### For Frontend Library

```bash
# 1. Make changes to src/js/src/
# 2. Run tests
npm run test --workspace=src/js

# 3. Run linting and formatting (handled by pre-commit or manually)
npx biome check --apply src/js/
```

---

## Code Standards

### Python Backend Standards

**See**: [`specs/guides/code-style.md`](./specs/guides/code-style.md)

**Key Points**:

- **Typing**: Fully typed with PEP 604 (`T | None`) - no `Optional[T]`.
- **No `from __future__ import annotations`** - use explicit stringification if needed.
- **Async/Await**: Use `async def` for I/O-bound operations where appropriate.
- **Docstrings**: Google Style for all public APIs.
- **Formatting & Linting**: Enforced by Ruff.

**Anti-Patterns to Avoid**:

- ❌ NO class-based tests (use function-based pytest).
- ❌ NO `Optional[T]` syntax.

### Frontend Standards

**See**: [`specs/guides/code-style.md`](./specs/guides/code-style.md)

**Key Points**:

- **Tooling**: All formatting and linting is handled by Biome.
- **TypeScript**: Use TypeScript for all new code to ensure type safety.
- **Modularity**: Keep code organized in modules.

---

## Testing Guidelines

**See**: [`specs/guides/testing.md`](./specs/guides/testing.md)

```bash
# Run the entire test suite (Python and TypeScript)
make test

# Run tests with coverage reporting for Python
make coverage

# Run Python tests in parallel
pytest -n auto src/py/tests/
```

**Standards**:

- **Frameworks**: `pytest` for Python, `Vitest` for TypeScript.
- **Coverage Target**: >90% for all new and modified code.
- **Fixtures**: Use pytest fixtures for setup/teardown in Python tests.
- **Async Tests**: Use `pytest-asyncio`.
- **Parallel**: All tests must be parallelizable.

---

## Documentation System

### Living Documentation in `specs/guides/`

The [`specs/guides/`](./specs/guides/) directory contains the **single source of truth** for project standards:

- **Architecture**: [`architecture.md`](./specs/guides/architecture.md) - System design and integration patterns.
- **Code Style**: [`code-style.md`](./specs/guides/code-style.md) - Python and TypeScript conventions.
- **Development Workflow**: [`development-workflow.md`](./specs/guides/development-workflow.md) - Process and tools.
- **Testing**: [`testing.md`](./specs/guides/testing.md) - Testing strategies and commands.

These guides must be kept in sync with the codebase.

### Workspace System (`specs/active/` and `specs/archive/`)

For **Gemini agents** following the structured workflow:

- `specs/active/` - Active development workspaces for features in progress.
- `specs/archive/` - Completed and archived workspaces.

These directories are gitignored and are used for the agent-based workflow management.

---

## Agent-Specific Workflows

### Gemini Agents (Structured Workflow)

Gemini agents follow a **comprehensive, checkpoint-based workflow** defined in [`.gemini/GEMINI.md`](./.gemini/GEMINI.md).

**Workflow Overview**:

1. **PRD Phase** (`/prd`) - Create a comprehensive Product Requirements Document in `specs/active/`. This phase is for planning and research only; no source code is modified.
2. **Implementation Phase** (`/implement`) - Write production-quality code based on the PRD, following all code standards.
3. **Testing Phase** (`/test`) - (Auto-invoked) Write a comprehensive test suite, ensuring >90% coverage, and test for edge cases.
4. **Review Phase** (`/review`) - (Auto-invoked) Verify all quality gates, run an anti-pattern scan, capture new knowledge in `specs/guides/`, and archive the work.

**Key Principles**:

- **Quality Gates**: All gates in `specs/guides/quality-gates.yaml` must pass.
- **Knowledge Capture**: New patterns must be documented in `specs/guides/` before work is considered complete.
- **No Shortcuts**: All checkpoints in the workflow are mandatory.

See [`.gemini/GEMINI.md`](./.gemini/GEMINI.md) for the complete workflow documentation.

### Other AI Assistants

1. Read this `AGENTS.md` document first.
2. Consult the relevant guides in `specs/guides/` for detailed patterns.
3. Follow the code standards for Python or TypeScript.
4. Run `make check-all` before considering work complete.
5. Update documentation when making significant changes.
