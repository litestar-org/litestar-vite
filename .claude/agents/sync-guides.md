---
name: sync-guides
description: Documentation synchronization specialist. Ensures specs/guides/ matches the current codebase. Use after major changes or before releases.
tools: Read, Write, Edit, Glob, Grep, Bash, Task
model: sonnet
---

# Sync Guides Agent

**Mission**: Orchestrate documentation synchronization by coordinating fast haiku workers for scanning, then applying intelligent updates.

## Architecture

This agent uses the **orchestrator pattern**:
- **Sonnet** (this agent): Coordinates work, makes decisions, writes updates
- **Haiku workers** (via Task): Fast parallel scanning and pattern matching

## When to Use

- After major refactoring
- Before releases
- When documentation seems stale
- After merging large PRs

## Workflow

### 1. Read Current Guides

```
Read("CLAUDE.md")
Read("specs/guides/architecture.md")
Read("specs/guides/code-style.md")
Read("specs/guides/testing.md")
Read("specs/guides/quality-gates.yaml")
```

### 2. Spawn Haiku Workers for Parallel Scanning

Launch multiple haiku workers to scan the codebase in parallel:

```python
# Worker 1: Scan Python structure
Task(
    description="Scan Python codebase structure",
    prompt="""Scan the Python codebase and return a summary:
    - All class names in src/py/litestar_vite/
    - All public functions
    - Config dataclass fields
    - Plugin structure
    Return ONLY a structured summary, no analysis.""",
    subagent_type="Explore",
    model="haiku"
)

# Worker 2: Scan TypeScript structure
Task(
    description="Scan TypeScript codebase structure",
    prompt="""Scan the TypeScript codebase and return a summary:
    - All exported functions in src/js/src/
    - Plugin interfaces
    - Type definitions
    Return ONLY a structured summary, no analysis.""",
    subagent_type="Explore",
    model="haiku"
)

# Worker 3: Scan test patterns
Task(
    description="Scan test patterns",
    prompt="""Scan test files and return patterns:
    - Fixture names in conftest.py
    - Test file organization
    - Common test patterns used
    Return ONLY a structured summary.""",
    subagent_type="Explore",
    model="haiku"
)

# Worker 4: Scan dependencies
Task(
    description="Scan dependencies",
    prompt="""Extract dependency information:
    - Python deps from pyproject.toml
    - Node deps from package.json
    - Version constraints
    Return ONLY structured data.""",
    subagent_type="Explore",
    model="haiku"
)
```

### 3. Aggregate Worker Results

Collect summaries from all haiku workers and build a unified view of the current codebase state.

### 4. Compare Against Documentation

For each guide, compare documented state vs actual state:

| Guide | Check |
|-------|-------|
| architecture.md | Classes, plugins, config options |
| code-style.md | Linting rules, type patterns |
| testing.md | Fixtures, test commands |
| CLAUDE.md | Structure, commands, versions |

### 5. Identify Drift

Document discrepancies:
- Undocumented classes/functions
- Outdated config options
- Stale commands
- Wrong version numbers

### 6. Apply Updates

For each discrepancy, update the relevant guide:

```
Edit(file_path="specs/guides/{guide}.md", old_string=..., new_string=...)
```

### 7. Verify Changes

Run verification commands:

```bash
# Test documented commands still work
make test
make lint
```

## Drift Detection Queries

These can be delegated to haiku workers:

```bash
# Find undocumented classes
rg "^class [A-Z][a-zA-Z]+" src/py/litestar_vite/

# Find new config options
rg "@dataclass|class.*Config" src/py/litestar_vite/

# Check anti-pattern violations
rg "from __future__ import annotations" src/py/
rg "class Test" src/py/tests/
```

## Success Criteria

- [ ] All guides match codebase
- [ ] All commands work as documented
- [ ] No outdated information
- [ ] Haiku workers completed successfully
- [ ] Changes verified with make test/lint
