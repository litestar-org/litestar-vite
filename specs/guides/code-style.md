# Code Style Guide for litestar-vite

This document defines the code style and quality standards for both the Python backend and TypeScript frontend. Consistency is enforced through automated tooling.

## General Principles

-   **Clarity**: Write code that is easy to read and understand.
-   **Explicitness**: Prefer explicit over implicit.
-   **Consistency**: Adhere to the existing code style in the project.

## Python Code Style

All Python code is automatically formatted and linted using tools configured in `pyproject.toml` and run via `pre-commit` hooks.

-   **Formatter**: [Ruff](https://docs.astral.sh/ruff/) is used for formatting, effectively replacing Black and isort.
-   **Linter**: [Ruff](https://docs.astral.sh/ruff/) is also used for linting, providing fast and comprehensive checks.
-   **Type Checking**: [MyPy](http://mypy-lang.org/) is used for static type checking.

### Key Standards

1.  **Type Hinting**:
    -   All functions and methods must have type hints for arguments and return values.
    -   Use modern type hints (PEP 604): `list[str]` instead of `List[str]`, and `str | None` instead of `Optional[str]`.
    -   Do **not** use `from __future__ import annotations`.

2.  **Docstrings**:
    -   All public modules, classes, functions, and methods must have a docstring.
    -   Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#3.8-comments-and-docstrings) for docstrings.

3.  **Imports**:
    -   Imports are automatically sorted by Ruff.
    -   Group imports logically (standard library, third-party, first-party).

### Tooling Commands

-   **Lint & Type-Check**: `make lint`
-   **Auto-format**: `make fix`

### Config Source of Truth
-   When both Python and Vite need the same values (asset/base URL, bundle/resource dirs, manifest), prefer setting them in `ViteConfig`. `set_environment()` writes `.litestar-vite.json` and the JS plugin uses it as defaults. Keep `vite.config.ts` overrides minimal.

## TypeScript/JavaScript Code Style

The frontend codebase (primarily in `src/js/` and `examples/`) is managed by [Biome](https://biomejs.dev/).

-   **Formatter**: Biome handles all code formatting.
-   **Linter**: Biome provides comprehensive linting rules.

Configuration is defined in `biome.json`.

### Key Standards

1.  **Formatting**:
    -   Follow the settings in `biome.json` (e.g., indentation, line width).
    -   Do not manually format code; let the tooling handle it.

2.  **Language Features**:
    -   Prefer modern ECMAScript features (e.g., `const`/`let` over `var`, arrow functions).
    -   Use TypeScript for all new code to ensure type safety.

### Tooling Commands

The pre-commit hooks automatically run Biome. To run it manually:

```bash
# Format and lint all relevant files
npx biome check --apply .
```

## Pre-Commit Hooks

This project uses `pre-commit` to ensure that all code committed to the repository meets our quality standards. The hooks are defined in `.pre-commit-config.yaml` and are installed automatically when you run `make install`.

The hooks will automatically run `ruff`, `biome`, `mypy`, and other checks before allowing a commit to be created.
