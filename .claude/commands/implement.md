---
description: Implement a feature from an existing PRD
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__zen__thinkdeep, mcp__zen__debug, mcp__zen__analyze
---

# Implementation Workflow

You are implementing the feature from: **specs/active/$ARGUMENTS**

## Phase 1: Load Context

1. Read the PRD and tasks:
   - `specs/active/$ARGUMENTS/prd.md`
   - `specs/active/$ARGUMENTS/tasks.md`
   - `specs/active/$ARGUMENTS/recovery.md`

2. Read project standards:
   - `CLAUDE.md`
   - `specs/guides/code-style.md`
   - `specs/guides/architecture.md`

## Phase 2: Research (if needed)

Complete any research tasks from the PRD:

- Use Context7 for library documentation
- Use WebSearch for best practices
- Use zen.thinkdeep for architectural decisions

## Phase 3: Implementation

Follow the task breakdown and implement each component:

### Python Code Standards
- Type hints: PEP 604 (`T | None`)
- Docstrings: Google style
- No `Optional[T]` or `from __future__ import annotations`
- Async for I/O operations
- Line length: 120 chars

### TypeScript Code Standards
- Use TypeScript strict mode
- Follow existing patterns in src/js/
- Use Biome formatting

### As You Work
- Update `tasks.md` progress
- Update `recovery.md` with current state
- Run tests frequently: `make test`
- Run linting: `make lint`

## Phase 4: Local Testing

Before completing implementation:

```bash
# Run tests
make test

# Run linting
make lint

# Check specific module coverage
pytest --cov=src/py/litestar_vite/{module} src/py/tests/
```

## Phase 5: Invoke Testing Agent

After all acceptance criteria met, auto-invoke testing:

```
Use the Task tool with subagent_type="testing" to run comprehensive tests.
```

## Phase 6: Invoke Docs & Vision Agent

After testing passes:

```
Use the Task tool with subagent_type="docs-vision" to run quality gates and documentation.
```

## Code Quality Checklist

Before invoking testing:
- [ ] All acceptance criteria from PRD met
- [ ] All functions have type hints (PEP 604)
- [ ] All public APIs have Google-style docstrings
- [ ] No `Optional[T]` usage
- [ ] No `from __future__ import annotations`
- [ ] Local tests pass
- [ ] Linting clean
