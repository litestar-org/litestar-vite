---
description: Create a PRD in any repo with auto-discovery
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Universal PRD Workflow

Creating PRD for: **$ARGUMENTS**

## Phase 0: Project Discovery

```bash
# Run project scan if available
if [ -f .claude/skills/universal-prd-implement/scripts/project_scan.py ]; then
  .claude/skills/universal-prd-implement/scripts/project_scan.py --format pretty
fi
```

Read key docs if present:
- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTRIBUTING.md` / `CONTRIBUTING.rst`

## Phase 1: Clarify Requirements

Ask for:
- Problem statement and users
- Acceptance criteria
- Constraints (performance, compatibility, deadlines)
- Out of scope items

## Phase 2: Choose PRD Location

- Prefer existing `specs/active/` style if present.
- Otherwise use `docs/specs/` or create `specs/active/` at repo root.

## Phase 3: Write PRD + Tasks + Recovery

Create:
- `prd.md`
- `tasks.md`
- `recovery.md`

Include:
- Goals, non-goals, acceptance criteria
- Affected files
- Testing strategy with discovered commands

## Phase 4: Report Next Steps

Summarize created files and the recommended `/implement` follow-up.
