---
description: Create a Product Requirements Document for a new feature
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__zen__planner, mcp__sequential-thinking__sequentialthinking
---

# PRD Creation Workflow

You are creating a Product Requirements Document for: **$ARGUMENTS**

## Phase 1: Understand the Request

First, gather context about the project and feature:

1. Read project documentation:
   - `CLAUDE.md` for project overview and standards
   - `specs/guides/architecture.md` for system design
   - `specs/guides/code-style.md` for coding standards

2. Search for related code:
   - Find similar existing implementations
   - Identify affected modules
   - Check existing patterns

## Phase 2: Deep Analysis

Use sequential thinking or zen.planner to thoroughly analyze:

1. What problem does this solve?
2. Who are the users/consumers?
3. What are the acceptance criteria?
4. What are the technical constraints?
5. What existing code will be affected?
6. What new code needs to be written?
7. What tests are needed?

## Phase 3: Research (if needed)

If the feature involves external libraries:

```
mcp__context7__resolve-library-id(libraryName="...")
mcp__context7__get-library-docs(...)
```

For best practices:
```
WebSearch(query="... best practices 2025")
```

## Phase 4: Create Workspace

Create the workspace directory structure:

```bash
mkdir -p specs/active/{slug}/research
mkdir -p specs/active/{slug}/tmp
```

## Phase 5: Write PRD

Create `specs/active/{slug}/prd.md` with this structure:

```markdown
# PRD: {Feature Name}

## Overview
- **Slug**: {slug}
- **Created**: {date}
- **Status**: Draft

## Problem Statement
{What problem does this solve? Who has this problem?}

## Goals
1. {Primary goal}
2. {Secondary goal}

## Non-Goals
- {What this feature will NOT do}

## Acceptance Criteria
- [ ] {Specific, testable criterion}
- [ ] {Specific, testable criterion}

## Technical Approach

### Architecture
{How it fits into existing codebase}

### Affected Files
- `src/py/litestar_vite/{file}.py` - {what changes}
- `src/js/src/{file}.ts` - {what changes}

### API Changes
{New or modified APIs}

## Testing Strategy
- Unit tests: {what to test}
- Integration tests: {scenarios}
- Edge cases: {list}

## Research Questions
- [ ] {Question that needs research}

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| {risk} | H/M/L | {mitigation} |
```

## Phase 6: Create Task Breakdown

Create `specs/active/{slug}/tasks.md`:

```markdown
# Tasks: {Feature Name}

## Phase 1: Planning ✓
- [x] Create PRD
- [x] Identify affected components

## Phase 2: Research
- [ ] Research {topic}

## Phase 3: Implementation
- [ ] Implement {component}

## Phase 4: Testing
- [ ] Write unit tests (90%+ coverage)
- [ ] Write integration tests

## Phase 5: Documentation
- [ ] Update docstrings
- [ ] Update guides if needed

## Phase 6: Quality Gate
- [ ] All tests pass
- [ ] Linting clean
- [ ] Archive workspace
```

## Phase 7: Create Recovery Guide

Create `specs/active/{slug}/recovery.md`:

```markdown
# Recovery Guide: {Feature Name}

## Current State
{Description of where development stands}

## Files Modified
- `{file}` - {status}

## Next Steps
1. {Next action to take}

## Context for Resumption
{Any important context for continuing this work}
```

## Completion Checklist

Before finishing:
- [ ] PRD is comprehensive with clear acceptance criteria
- [ ] Tasks are specific and measurable
- [ ] Recovery guide enables session resumption
- [ ] Research questions are identified
- [ ] Follows litestar-vite patterns from specs/guides/
