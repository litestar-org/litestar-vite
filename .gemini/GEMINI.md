# Gemini Agent System for litestar-vite

This document provides behavioral instructions and project context for Gemini CLI agents.

---

## ⚠️ BEHAVIORAL REQUIREMENTS (READ FIRST)

### Core Principles

1. **Verify Before Acting** - Never assume; always confirm understanding
2. **Research Before Implementing** - Search codebase and docs first
3. **Follow Existing Patterns** - Match the style of surrounding code
4. **Ask When Uncertain** - Questions are better than wrong assumptions

### Before ANY Code Changes

You MUST complete these steps before modifying source code:

1. **Verify Understanding**
   - Restate the task in your own words
   - Identify what success looks like
   - List the components that will be affected

2. **Search First**
   - Use `grep`/`find` to locate relevant existing code
   - Read similar implementations in the codebase
   - Check `specs/guides/` for documented patterns

3. **Check Patterns**
   - Read existing code that does similar things
   - Match the naming conventions used
   - Follow the error handling patterns

4. **Identify Unknowns**
   - List things you're not certain about
   - If more than 2 unknowns, research before proceeding

### When Uncertain

- ❌ **DO NOT** proceed with assumptions
- ❌ **DO NOT** invent new patterns when existing ones exist
- ✅ **DO** use Context7 for library documentation
- ✅ **DO** use Sequential Thinking for complex analysis
- ✅ **DO** ask clarifying questions
- ✅ **DO** search the codebase first

### STOP Conditions

**Stop and ask the user if**:

- More than 3 files need modification without explicit approval
- You cannot find similar patterns in the codebase
- The technical approach is unclear
- Requirements seem contradictory or ambiguous
- You're about to delete or significantly refactor existing code

### Introspection Markers

Use these markers when reasoning through complex tasks:

- 🧠 **Meta-Analysis**: Why am I choosing this approach?
- 🎯 **Decision Logic**: What evidence supports this?
- 🔄 **Alternative**: What other approaches exist?
- 📊 **Evidence Check**: Does the code confirm this assumption?
- 💡 **Learning**: What did I discover?
- ⚡ **Correction**: Adjusting based on new information

### Confidence Assessment

Before major actions, assess your confidence:

- **HIGH (>90%)**: Clear requirements, found patterns, no unknowns → Proceed
- **MEDIUM (60-90%)**: Some uncertainties but reasonable assumptions → Document assumptions, proceed carefully
- **LOW (<60%)**: Significant unknowns → Research more or ask user

---

## Project Overview

- **Name**: `litestar-vite`
- **Description**: Integration between Litestar Python framework and Vite.js frontend tooling, with Inertia.js support
- **Languages**: Python, TypeScript
- **Frameworks**: Litestar (backend), Vite (frontend)
- **Testing**: pytest (Python), Vitest (TypeScript)
- **Linting**: ruff, mypy (Python), Biome (TypeScript)

## Code Style Requirements (CRITICAL)

### Python

- **Type hints**: Use `T | None` (PEP 604), **NOT** `Optional[T]`
- **No future annotations**: Never use `from __future__ import annotations`
- **Async/await**: All I/O operations must be async
- **Docstrings**: Google style for all public APIs
- **Tests**: Function-based pytest, **NOT** class-based

### TypeScript

- **Strict mode**: All TypeScript must pass strict checks
- **Types**: Prefer interfaces for objects, types for unions
- **Async**: Use async/await, not .then() chains

## Checkpoint-Based Workflow

This project uses a rigorous, checkpoint-based workflow. All work is managed through specs in the `specs/` directory.

### Feature Lifecycle

1. **Planning (`/prd`)**: Create Product Requirements Document
2. **Implementation (`/implement`)**: Write code based on PRD
3. **Testing (`/test`)**: Create comprehensive test suite
4. **Review (`/review`)**: Verify quality gates and archive

### Quality Gates

All code must pass:

- **Tests**: `make test` - All tests passing
- **Linting**: `make lint` - Zero errors
- **Type Checking**: `make type-check` - Zero errors
- **Coverage**: 90%+ for modified modules
- **Anti-patterns**: No `Optional[T]`, no `__future__`, no class-based tests

## Key Commands

```bash
# Development
make install          # Install dependencies
make test            # Run all tests
make lint            # Check for errors
make fix             # Auto-fix formatting
make check-all       # Run all checks

# Gemini workflow
gemini /prd "feature description"    # Start planning
gemini /implement <slug>             # Implement from PRD
gemini /test <slug>                  # Run testing phase
gemini /review <slug>                # Quality gate and archive
```

## Available Context

Context files are loaded from `.gemini/context/`:

- `litestar.md` - Litestar framework patterns
- `vite.md` - Vite build tool patterns
- `inertia.md` - Inertia.js integration
- `testing.md` - Testing patterns
- `react.md` - React integration
- `vue.md` - Vue integration
- `svelte.md` - Svelte integration
- `code-style.md` - Code style quick reference

## MCP Tools Available

### Context7 (Library Documentation)

```python
# Resolve library ID first
mcp__context7__resolve-library-id(libraryName="litestar")

# Then fetch docs
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="dependency injection",
    tokens=5000
)
```

### Sequential Thinking (Complex Analysis)

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: Analyze the requirement",
    thought_number=1,
    total_thoughts=10,
    next_thought_needed=True
)
```

Use Sequential Thinking for:
- Complex architectural decisions
- Multi-step problem solving
- When you need to reason through trade-offs

## Project Structure

```
src/py/litestar_vite/     # Python library
├── config.py             # ViteConfig
├── plugin.py             # VitePlugin
├── loader.py             # ViteAssetLoader
├── inertia/              # Inertia.js support
src/js/src/               # TypeScript library
├── index.ts              # Vite plugin
examples/                 # Example applications
specs/                    # Documentation and specs
├── guides/               # Living documentation
├── active/               # Active workspaces
└── archive/              # Completed work
```

## Remember

1. **Read before writing** - Always read existing code first
2. **Match existing patterns** - Don't invent new conventions
3. **Test everything** - 90%+ coverage required
4. **Document decisions** - Explain non-obvious choices
5. **Ask when uncertain** - Questions prevent mistakes
