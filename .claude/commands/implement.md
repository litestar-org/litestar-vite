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
- No `from __future__ import annotations`
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

## Phase 4.5: Update Skills (if applicable)

When implementation introduces or modifies:

- **Integration patterns** (new ViteConfig options, Inertia helpers, etc.)
- **Framework-specific code** (React, Vue, Svelte hooks/patterns)
- **CLI commands** or workflows
- **Type generation** outputs or consumption patterns
- **Breaking changes** to existing APIs

**Update the relevant personal skills in `~/.claude/skills/`:**

1. Identify affected skills:

   ```bash
   ls ~/.claude/skills/
   # react, vue, svelte, angular, litestar, vite, inertia, htmx, nuxt, testing
   ```

2. Update the `## Litestar-Vite Integration` section in each affected skill:
   - Add new configuration options
   - Update code examples
   - Add new helpers or utilities
   - Document breaking changes

3. Also update project-specific skills in `.claude/skills/` if patterns are unique to this project:
   - `litestar-assets-cli/`
   - `litestar-vite-integration/`
   - `litestar-vite-typegen/`

4. Document new patterns in `tmp/new-patterns.md` for extraction during review

**Example skill updates:**

```markdown
# If you added a new Inertia helper like `scroll_props()`:
# Update ~/.claude/skills/inertia/SKILL.md

## Inertia Response Helpers

```python
from litestar_vite.inertia import (
    ...
    scroll_props,     # NEW: Control scroll behavior in pagination
)
```

```

```markdown
# If you changed ViteConfig modes:
# Update ~/.claude/skills/litestar/SKILL.md and ~/.claude/skills/vite/SKILL.md
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
- [ ] No `from __future__ import annotations`
- [ ] Local tests pass
- [ ] Linting clean
- [ ] Personal skills updated (if patterns changed) in `~/.claude/skills/`
- [ ] New patterns documented in `tmp/new-patterns.md`
