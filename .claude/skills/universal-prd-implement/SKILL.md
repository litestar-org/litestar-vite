---
name: universal-prd-implement
description: Create PRDs and implement features in any repository with auto-discovery of tools, commands, and documentation. Use when a user asks for /prd, /implement, planning, or implementation workflows across unknown stacks, and when you need a tool-agnostic, self-discovering process.
---

# Universal PRD + Implement

## Overview
Use a self-discovering workflow to create PRDs and implement features across any stack.

## Core Workflow (tool-agnostic)

### 1) Discover the project

Prefer the bundled scanner:

```bash
.claude/skills/universal-prd-implement/scripts/project_scan.py --format pretty
```

If the scanner isn’t available, manually inspect:

- `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.*`
- `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`
- `Makefile`, `scripts/`, `docs/`, `specs/`

### 2) Choose PRD location

Decision order:

1. If `specs/active/` exists, use `specs/active/{slug}/`.
2. Else if `docs/specs/` exists, use `docs/specs/{slug}/`.
3. Else create `specs/active/{slug}/`.

### 3) Determine commands

Use discovered commands first:

- Prefer `make test`, `make lint`, `make build` if targets exist.
- Else use package manager scripts (`npm run test`, `pnpm test`, etc.).
- Else fall back to language defaults (`pytest`, `go test`, `cargo test`, `mvn test`).

### 4) PRD output (when asked for /prd)

Create:

- `prd.md`
- `tasks.md`
- `recovery.md`

Keep acceptance criteria testable and include discovered commands.

### 5) Implementation output (when asked for /implement)

- Read PRD and tasks.
- Identify affected files with `rg` (fallback `grep` if needed).
- Implement incrementally.
- Update tasks and recovery notes.
- Run discovered tests/linters.

## Templates (portable slash commands)

Copy these into a repo’s `.claude/commands/` to enable `/prd` and `/implement` in any project:

- `assets/commands/prd.md`
- `assets/commands/implement.md`

Install them with the bootstrap helper:

```bash
.claude/skills/universal-prd-implement/scripts/bootstrap_commands.py /path/to/repo
```

## Resources

### scripts/

- `scripts/project_scan.py`: tool-agnostic repo scanner (outputs languages, frameworks, commands, PRD location)
- `scripts/bootstrap_commands.py`: install `/prd` and `/implement` into a target repo

### assets/

- `assets/commands/prd.md`: portable PRD slash command
- `assets/commands/implement.md`: portable implementation slash command
