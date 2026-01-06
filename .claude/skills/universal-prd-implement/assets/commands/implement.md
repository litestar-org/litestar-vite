---
description: Implement a PRD in any repo with auto-discovery
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Universal Implementation Workflow

Implementing: **$ARGUMENTS**

## Phase 0: Load PRD + Tasks

Locate PRD and tasks from the project’s chosen PRD root.

## Phase 1: Project Discovery

```bash
# Run project scan if available
if [ -f .claude/skills/universal-prd-implement/scripts/project_scan.py ]; then
  .claude/skills/universal-prd-implement/scripts/project_scan.py --format pretty
fi
```

## Phase 2: Analyze Affected Areas

- Search for similar patterns in code.
- Identify tests to extend.
- Confirm coding standards from repo docs.

## Phase 3: Implement

- Follow repo style and architecture.
- Update tasks.md with progress.
- Add tests per acceptance criteria.

## Phase 4: Verify

Run discovered commands:
- tests
- lint
- type check

## Phase 5: Report

Summarize changes and next steps.
