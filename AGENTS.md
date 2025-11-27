# AI Agent Guidelines for litestar-vite

**Version**: 2.0
**Last Updated**: 2025-11-26

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
9. [Claude Agent System](#claude-agent-system)
10. [MCP Tools Available](#mcp-tools-available)
11. [Quality Gates](#quality-gates)

---

## Project Overview

**litestar-vite** is a library that provides seamless integration between the [Litestar](https://litestar.dev/) Python web framework and the [Vite](https://vitejs.dev/) next-generation frontend tooling. It includes support for [Inertia.js](https://inertiajs.com/) to facilitate the creation of modern single-page applications (SPAs) with server-side routing.

The project consists of:

- **Core Library**: A Python library (`litestar_vite`) that provides the Litestar plugin, asset loading, and Inertia support.
- **JS Library**: A small TypeScript library (`src/js`) that provides helper functions for the frontend.
- **Examples**: A collection of example projects (`examples/`) demonstrating various use cases (basic, Inertia with Vue, etc.).

### Technology Stack

#### Backend (Python)

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.9+ |
| **Framework** | Litestar |
| **Testing** | pytest, pytest-asyncio, pytest-xdist |
| **Linting** | Ruff |
| **Type Checking** | MyPy, Pyright, Basedpyright |
| **Package Manager** | uv |

#### Frontend (TypeScript)

| Component | Technology |
|-----------|------------|
| **Language** | TypeScript |
| **Build Tool** | Vite (5.x, 6.x, 7.x) |
| **Testing** | Vitest |
| **Linting** | Biome |
| **Package Manager** | npm |

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
├── .claude/                    # Claude agent system
│   └── agents/                 # Specialized agent definitions
│       ├── prd.md             # PRD creation agent
│       ├── expert.md          # Implementation agent
│       ├── testing.md         # Testing agent
│       ├── docs-vision.md     # Documentation & quality gate agent
│       └── sync-guides.md     # Documentation sync agent
├── .gemini/                    # Gemini agent workflow system
│   ├── GEMINI.md              # Gemini-specific workflow documentation
│   └── commands/              # Custom slash commands (prd, implement, etc.)
├── specs/                      # Comprehensive project specifications
│   ├── guides/                # Living documentation and patterns
│   │   ├── architecture.md
│   │   ├── code-style.md
│   │   ├── development-workflow.md
│   │   ├── testing.md
│   │   └── quality-gates.yaml
│   ├── active/                # Active development workspaces (gitignored)
│   ├── archive/               # Archived completed work (gitignored)
│   └── template-spec/         # Workspace templates
├── src/
│   ├── py/litestar_vite/      # Core Python library source
│   │   ├── inertia/           # Inertia.js integration
│   │   │   ├── config.py      # InertiaConfig
│   │   │   ├── plugin.py      # InertiaPlugin
│   │   │   ├── middleware.py  # InertiaMiddleware
│   │   │   ├── response.py    # InertiaResponse
│   │   │   ├── request.py     # InertiaRequest
│   │   │   └── helpers.py     # Helper functions
│   │   ├── templates/         # Jinja2 templates for scaffolding
│   │   ├── config.py          # ViteConfig
│   │   ├── plugin.py          # VitePlugin
│   │   ├── loader.py          # ViteAssetLoader
│   │   ├── commands.py        # CLI commands
│   │   └── cli.py             # CLI entry points
│   └── js/                    # Core TypeScript library source
│       ├── src/
│       │   ├── index.ts       # Vite plugin
│       │   └── inertia-helpers/
│       └── tests/
├── examples/                   # Example applications
│   ├── basic/
│   ├── inertia/
│   ├── flash/
│   └── jinja/
├── tests/                      # Additional Python tests
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
npm run test

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
- **Line Length**: 120 characters.

**Anti-Patterns to Avoid**:

| Pattern | Why It's Bad | Use Instead |
|---------|--------------|-------------|
| `from __future__ import annotations` | Project standard | Explicit string annotations |
| `Optional[T]` | Old syntax | `T \| None` (PEP 604) |
| `class TestFoo:` in tests | Project standard | Function-based pytest |
| `hasattr()`/`getattr()` | Type safety | Type guards, explicit checks |
| Nested `try/except` blocks | Complexity | Flat error handling |
| Mutable default arguments | Dangerous | `None` with conditional |

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
- **Async Tests**: Use `pytest-asyncio` (auto mode enabled).
- **Parallel**: All tests must be parallelizable.

### Required Test Types

1. **Unit tests** - Test components in isolation
2. **Integration tests** - Test with real dependencies
3. **Edge cases** - NULL, empty, error conditions
4. **Performance tests** - N+1 query detection (for database ops)
5. **Concurrent tests** - Race conditions (for shared state)

---

## Documentation System

### Living Documentation in `specs/guides/`

The [`specs/guides/`](./specs/guides/) directory contains the **single source of truth** for project standards:

- **Architecture**: [`architecture.md`](./specs/guides/architecture.md) - System design and integration patterns.
- **Code Style**: [`code-style.md`](./specs/guides/code-style.md) - Python and TypeScript conventions.
- **Development Workflow**: [`development-workflow.md`](./specs/guides/development-workflow.md) - Process and tools.
- **Testing**: [`testing.md`](./specs/guides/testing.md) - Testing strategies and commands.
- **Quality Gates**: [`quality-gates.yaml`](./specs/guides/quality-gates.yaml) - Automated checks.

These guides must be kept in sync with the codebase.

### Workspace System (`specs/active/` and `specs/archive/`)

For agents following the structured workflow:

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

---

## Claude Agent System

Claude Code uses a **multi-agent system** where specialized agents handle specific phases of development.

### Agent Architecture

| Agent | File | Mission |
|-------|------|---------|
| **PRD** | `.claude/agents/prd.md` | Requirements analysis, PRD creation, task breakdown |
| **Expert** | `.claude/agents/expert.md` | Implementation with deep technical knowledge |
| **Testing** | `.claude/agents/testing.md` | Comprehensive test creation (90%+ coverage) |
| **Docs & Vision** | `.claude/agents/docs-vision.md` | Documentation, quality gate, knowledge capture |
| **Sync Guides** | `.claude/agents/sync-guides.md` | Documentation synchronization |

### Sequential Development Phases

1. **Phase 1: PRD** - Agent creates workspace in `specs/active/{slug}/`
2. **Phase 2: Expert Research** - Research patterns, libraries, best practices
3. **Phase 3: Implementation** - Expert writes production code
4. **Phase 4: Testing** - Testing agent creates comprehensive tests (auto-invoked by Expert)
5. **Phase 5: Documentation** - Docs & Vision updates guides (auto-invoked after Testing)
6. **Phase 6: Quality Gate** - Full validation and knowledge capture
7. **Phase 7: Archive** - Workspace moved to `specs/archive/`

### Invoking Claude Agents

```python
# Start a new feature with PRD
Task(
    description="Create PRD for new feature",
    prompt="Create PRD for: [feature description]",
    subagent_type="prd"
)

# Implement from PRD
Task(
    description="Implement feature",
    prompt="Implement feature from specs/active/{slug}",
    subagent_type="expert"
)

# Sync documentation
Task(
    description="Sync documentation",
    prompt="Ensure specs/guides/ matches codebase",
    subagent_type="sync-guides"
)
```

### Workspace Structure

```
specs/active/{slug}/
├── prd.md          # Product Requirements Document
├── tasks.md        # Implementation checklist
├── recovery.md     # Session resume instructions
├── research/       # Research findings
│   └── plan.md     # Research plan
└── tmp/            # Temporary files (gitignored)
```

---

## MCP Tools Available

### Context7 (Library Documentation)

```python
# Resolve library ID
mcp__context7__resolve-library-id(libraryName="litestar")

# Fetch documentation
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="dependency injection",
    tokens=5000
)
```

### Zen MCP (Analysis & Planning)

- **zen.planner**: Multi-step planning with revision capabilities
- **zen.chat**: Collaborative thinking and brainstorming
- **zen.thinkdeep**: Deep architectural analysis
- **zen.analyze**: Code quality and performance analysis
- **zen.debug**: Systematic debugging workflow
- **zen.consensus**: Multi-model consensus for decisions

### Sequential Thinking

Use for deep analysis requiring 12+ steps:

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: Analyze feature scope",
    thought_number=1,
    total_thoughts=15,
    next_thought_needed=True
)
```

### WebSearch

Use for researching best practices and modern patterns:

```python
WebSearch(query="litestar assets integration best practices 2025")
```

---

## Quality Gates

All code must pass these gates (defined in `specs/guides/quality-gates.yaml`):

### Implementation Gates

- [ ] `make test` passes
- [ ] `make lint` passes (zero errors)
- [ ] `make type-check` passes

### Testing Gates

- [ ] 90%+ coverage for modified modules
- [ ] Tests run in parallel (`pytest -n auto`)
- [ ] N+1 query detection (if database ops)
- [ ] Concurrent access tests (if shared state)

### Documentation Gates

- [ ] No anti-patterns in code
- [ ] `specs/guides/` updated if new patterns introduced
- [ ] Knowledge captured before archival

---

## Knowledge Capture Protocol

After every significant feature:

1. **Update guides** - Add new patterns to `specs/guides/`
2. **Document APIs** - Ensure all public APIs have docstrings
3. **Add examples** - Include working code examples
4. **Update AGENTS.md** - If workflow improves

---

## Version Control Guidelines

- **Branch Strategy**: Feature branches from `main`
- **Commit Style**: Conventional commits (`feat:`, `fix:`, `chore:`, etc.)
- **PR Requirements**: All quality gates must pass
- **No force push** to `main`

---

## Other AI Assistants

1. Read this `AGENTS.md` document first.
2. Consult the relevant guides in `specs/guides/` for detailed patterns.
3. Follow the code standards for Python or TypeScript.
4. Run `make check-all` before considering work complete.
5. Update documentation when making significant changes.
