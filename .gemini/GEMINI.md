# Gemini Agent System for litestar-vite

This document outlines the configuration and workflow for the Gemini agent system integrated into the `litestar-vite` project.

## Project Overview

- **Name**: `litestar-vite`
- **Description**: A project integrating the Litestar Python framework with the Vite.js frontend build tool, with support for Inertia.js.
- **Languages**: Python, TypeScript
- **Frameworks**: Litestar (backend), Vite (frontend)
- **Testing**: pytest (Python), Vitest (TypeScript)
- **Linting**: ruff, mypy (Python), Biome (TypeScript)

## Checkpoint-Based Workflow

This project uses a rigorous, checkpoint-based workflow to ensure high-quality contributions. All work is managed through specs in the `specs/` directory and executed via Gemini commands.

The lifecycle of a feature is:
1.  **Planning (`/prd`)**: A Product Requirements Document is created.
2.  **Implementation (`/implement`)**: Code is written based on the PRD.
3.  **Testing (`/test`)**: A comprehensive test suite is created.
4.  **Review (`/review`)**: Quality gates are verified and work is archived.

Each command follows a strict sequence of checkpoints defined in its respective `.toml` file in `.gemini/commands/`.

## Key Commands

- `gemini /prd "feature description"`: Starts the planning phase for a new feature.
- `gemini /implement <slug>`: Starts the implementation phase using an approved PRD.
- `gemini /test <slug>`: (Auto-invoked) Starts the testing phase.
- `gemini /review <slug>`: (Auto-invoked) Starts the final review and archival phase.

## Quality Gates

All code must pass a series of automated quality gates defined in `specs/guides/quality-gates.yaml`. These include:

- **Tests**: All tests must pass (`make test`).
- **Linting**: Code must be free of linting errors (`make lint`).
- **Type Checking**: Code must pass static type analysis (`make type-check`).
- **Test Coverage**: Modified modules must have at least 90% test coverage.
- **Anti-Patterns**: Code is scanned for critical anti-patterns (e.g., use of `Optional[T]`).

Failure to meet these gates will block the workflow.
