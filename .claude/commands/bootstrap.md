---
description: Bootstrap AI development infrastructure for any project
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking
---

# Project Bootstrap Command

**Version**: 1.0 | **Bootstrap Framework**: litestar-vite

You are bootstrapping AI development infrastructure for this project. This command will analyze the codebase, detect frameworks and patterns, and generate comprehensive Claude Code configuration including commands, agents, skills, and the PRD-driven development workflow.

---

## Table of Contents

1. [Preflight Checks](#part-1-preflight-checks)
2. [Detection Phase](#part-2-detection-phase)
3. [Generation Phase](#part-3-generation-phase)
4. [Alignment Mode](#part-4-alignment-mode)
5. [Verification](#part-5-verification)
6. [Embedded Templates](#part-6-embedded-templates)
7. [Framework Knowledge Base](#part-7-framework-knowledge-base)

---

## Part 1: Preflight Checks

### Step 1.1: Environment Validation

Before proceeding, verify we're in a valid project:

```bash
# Check for git repository
test -d .git && echo "GIT_REPO=true" || echo "GIT_REPO=false"

# Check for common project markers
test -f package.json && echo "HAS_PACKAGE_JSON=true"
test -f pyproject.toml && echo "HAS_PYPROJECT=true"
test -f Cargo.toml && echo "HAS_CARGO=true"
test -f go.mod && echo "HAS_GO_MOD=true"
test -f pom.xml && echo "HAS_POM=true"
```

**If no project markers found**: Ask user to confirm this is the correct directory.

### Step 1.2: Detect Existing Bootstrap

Check if this project has already been bootstrapped:

```bash
# Check for existing Claude configuration
test -d .claude && echo "CLAUDE_EXISTS=true"
test -f CLAUDE.md && echo "CLAUDE_MD_EXISTS=true"
test -d .claude/commands && echo "CLAUDE_COMMANDS_EXISTS=true"
test -d .claude/skills && echo "CLAUDE_SKILLS_EXISTS=true"
test -d .claude/agents && echo "CLAUDE_AGENTS_EXISTS=true"

# Check for specs structure
test -d specs/guides && echo "SPECS_EXISTS=true"
test -d specs/active && echo "SPECS_ACTIVE_EXISTS=true"
```

**If existing bootstrap detected**:
- Enter ALIGNMENT MODE (Part 4)
- Preserve custom additions
- Update to latest patterns

**If fresh project**:
- Continue with full bootstrap

### Step 1.3: Get User Confirmation

Before proceeding, confirm with user:

```
This bootstrap will create/update:
- CLAUDE.md (main AI instructions)
- .claude/commands/ (6 slash commands)
- .claude/agents/ (4 subagents)
- .claude/skills/ (per-detected-framework)
- .claude/settings.local.json (permissions)
- specs/ directory structure (guides, active, archive)

Detected mode: [FRESH | ALIGNMENT]

Proceed? [Y/n]
```

---

## Part 2: Detection Phase

### Step 2.1: Language Detection

Scan for primary language indicators:

```bash
# Python indicators
test -f pyproject.toml && echo "LANG_PYTHON=true"
test -f setup.py && echo "LANG_PYTHON=true"
test -f requirements.txt && echo "LANG_PYTHON=true"
test -f poetry.lock && echo "LANG_PYTHON=true"
test -f uv.lock && echo "LANG_PYTHON=true"

# JavaScript/TypeScript indicators
test -f package.json && echo "LANG_JS=true"
test -f tsconfig.json && echo "LANG_TS=true"

# Other languages
test -f Cargo.toml && echo "LANG_RUST=true"
test -f go.mod && echo "LANG_GO=true"
test -f pom.xml && echo "LANG_JAVA=true"
test -f build.gradle && echo "LANG_KOTLIN=true"
```

### Step 2.2: Framework Detection - Python

Parse pyproject.toml or requirements.txt for frameworks:

```bash
# Web frameworks
grep -i "litestar" pyproject.toml 2>/dev/null && echo "PY_LITESTAR=true"
grep -i "fastapi" pyproject.toml 2>/dev/null && echo "PY_FASTAPI=true"
grep -i "flask" pyproject.toml 2>/dev/null && echo "PY_FLASK=true"
grep -i "django" pyproject.toml 2>/dev/null && echo "PY_DJANGO=true"
grep -i "starlette" pyproject.toml 2>/dev/null && echo "PY_STARLETTE=true"

# Database/ORM
grep -i "sqlalchemy" pyproject.toml 2>/dev/null && echo "PY_SQLALCHEMY=true"
grep -i "advanced-alchemy" pyproject.toml 2>/dev/null && echo "PY_ADVANCED_ALCHEMY=true"
grep -i "tortoise" pyproject.toml 2>/dev/null && echo "PY_TORTOISE=true"

# Testing
grep -i "pytest" pyproject.toml 2>/dev/null && echo "PY_PYTEST=true"
grep -i "pytest-asyncio" pyproject.toml 2>/dev/null && echo "PY_PYTEST_ASYNCIO=true"

# Linting
grep -i "ruff" pyproject.toml 2>/dev/null && echo "PY_RUFF=true"
grep -i "mypy" pyproject.toml 2>/dev/null && echo "PY_MYPY=true"
grep -i "black" pyproject.toml 2>/dev/null && echo "PY_BLACK=true"
```

### Step 2.3: Framework Detection - JavaScript/TypeScript

Parse package.json for frameworks:

```bash
# UI Frameworks
grep '"react"' package.json 2>/dev/null && echo "JS_REACT=true"
grep '"vue"' package.json 2>/dev/null && echo "JS_VUE=true"
grep '"svelte"' package.json 2>/dev/null && echo "JS_SVELTE=true"
grep '"@angular/core"' package.json 2>/dev/null && echo "JS_ANGULAR=true"
grep '"solid-js"' package.json 2>/dev/null && echo "JS_SOLID=true"

# Meta-frameworks
grep '"next"' package.json 2>/dev/null && echo "JS_NEXT=true"
grep '"nuxt"' package.json 2>/dev/null && echo "JS_NUXT=true"
grep '"@sveltejs/kit"' package.json 2>/dev/null && echo "JS_SVELTEKIT=true"
grep '"astro"' package.json 2>/dev/null && echo "JS_ASTRO=true"

# Build tools
grep '"vite"' package.json 2>/dev/null && echo "JS_VITE=true"
grep '"webpack"' package.json 2>/dev/null && echo "JS_WEBPACK=true"
grep '"esbuild"' package.json 2>/dev/null && echo "JS_ESBUILD=true"

# Integration
grep '"@inertiajs"' package.json 2>/dev/null && echo "JS_INERTIA=true"
grep '"htmx.org"' package.json 2>/dev/null && echo "JS_HTMX=true"

# Testing
grep '"vitest"' package.json 2>/dev/null && echo "JS_VITEST=true"
grep '"jest"' package.json 2>/dev/null && echo "JS_JEST=true"
grep '"@testing-library"' package.json 2>/dev/null && echo "JS_TESTING_LIBRARY=true"

# Linting
grep '"biome"' package.json 2>/dev/null && echo "JS_BIOME=true"
grep '"eslint"' package.json 2>/dev/null && echo "JS_ESLINT=true"
grep '"prettier"' package.json 2>/dev/null && echo "JS_PRETTIER=true"
```

### Step 2.4: Build System Detection

Identify how the project builds and tests:

```bash
# Makefile
test -f Makefile && echo "BUILD_MAKE=true"
grep "test:" Makefile 2>/dev/null && echo "TEST_CMD_MAKE=true"
grep "lint:" Makefile 2>/dev/null && echo "LINT_CMD_MAKE=true"

# npm scripts
grep '"test"' package.json 2>/dev/null && echo "TEST_CMD_NPM=true"
grep '"lint"' package.json 2>/dev/null && echo "LINT_CMD_NPM=true"
grep '"build"' package.json 2>/dev/null && echo "BUILD_CMD_NPM=true"

# Python package managers
test -f uv.lock && echo "PKG_UV=true"
test -f poetry.lock && echo "PKG_POETRY=true"
test -f Pipfile.lock && echo "PKG_PIPENV=true"
```

### Step 2.5: Code Style Detection

Sample code files to detect patterns:

```bash
# Python type hint style
grep -r "Optional\[" src/ 2>/dev/null | head -5 && echo "STYLE_OPTIONAL=true"
grep -r "| None" src/ 2>/dev/null | head -5 && echo "STYLE_PEP604=true"

# Future annotations
grep -r "from __future__ import annotations" src/ 2>/dev/null && echo "STYLE_FUTURE_ANNOTATIONS=true"

# Test style
grep -r "class Test" tests/ 2>/dev/null | head -3 && echo "STYLE_CLASS_TESTS=true"
grep -r "^def test_" tests/ 2>/dev/null | head -3 && echo "STYLE_FUNC_TESTS=true"

# Docstring style (sample first docstring)
grep -A2 '"""' src/*.py 2>/dev/null | head -10
```

**Determine code style from samples**:
- If `STYLE_PEP604=true`: Use `T | None` pattern
- If `STYLE_OPTIONAL=true` and not `STYLE_PEP604`: Use `Optional[T]` pattern
- If `STYLE_FUNC_TESTS=true`: Use function-based tests
- If `STYLE_CLASS_TESTS=true`: Use class-based tests

### Step 2.6: Build Detection Profile

Compile all detections into a profile:

```markdown
## Detection Profile

### Languages
- Primary: {python|typescript|rust|go|java}
- Secondary: {list}

### Python Frameworks
- Web: {litestar|fastapi|flask|django}
- ORM: {sqlalchemy|advanced-alchemy|tortoise}
- Testing: {pytest|pytest-asyncio}
- Linting: {ruff|mypy|black}

### JavaScript Frameworks
- UI: {react|vue|svelte|angular}
- Meta: {next|nuxt|sveltekit|astro}
- Build: {vite|webpack|esbuild}
- Integration: {inertia|htmx}
- Testing: {vitest|jest}
- Linting: {biome|eslint|prettier}

### Build System
- Type: {make|npm|uv|poetry}
- Test command: {make test|npm test|uv run pytest}
- Lint command: {make lint|npm run lint|uv run ruff}

### Code Style
- Type hints: {pep604|optional|none}
- Docstrings: {google|numpy|sphinx}
- Test style: {function|class}
- Line length: {80|120|default}

### Anti-Patterns to Enforce
- {based on opposite of detected style}
```

---

## Part 3: Generation Phase

### Step 3.1: Create Directory Structure

```bash
# Create Claude directories
mkdir -p .claude/commands
mkdir -p .claude/agents
mkdir -p .claude/skills

# Create specs directories
mkdir -p specs/guides
mkdir -p specs/guides/workflows
mkdir -p specs/active
mkdir -p specs/archive

# Create .gitkeep files
touch specs/active/.gitkeep
touch specs/archive/.gitkeep
```

### Step 3.2: Generate CLAUDE.md

Create the main Claude instructions file using the CLAUDE.md template from Part 6, substituting:
- `{PROJECT_NAME}`: From package.json name or pyproject.toml name
- `{PROJECT_DESCRIPTION}`: From package.json description or pyproject.toml description
- `{DATE}`: Current date
- `{BACKEND_STACK}`: Detected Python frameworks
- `{FRONTEND_STACK}`: Detected JS frameworks
- `{TEST_FRAMEWORK}`: pytest, vitest, jest, etc.
- `{LINT_TOOLS}`: ruff, biome, eslint, etc.
- `{PACKAGE_MANAGER}`: uv, npm, poetry, etc.
- `{ESSENTIAL_COMMANDS}`: Based on build system detection
- `{CODE_STANDARDS}`: Based on code style detection
- `{SKILLS_LIST}`: Based on detected frameworks
- `{ANTI_PATTERNS}`: Based on code style detection

### Step 3.3: Generate Commands

Generate 6 core slash commands:

1. **prd.md** - PRD creation workflow
2. **implement.md** - Implementation workflow
3. **test.md** - Testing workflow
4. **review.md** - Quality gate and archive
5. **explore.md** - Codebase exploration
6. **fix-issue.md** - GitHub issue fixing

Use templates from Part 6, customizing:
- Test commands based on detected test framework
- Lint commands based on detected linting tools
- Project structure based on detected layout

### Step 3.4: Generate Agents

Generate 4 subagent definitions:

1. **prd.md** - PRD specialist agent
2. **expert.md** - Implementation specialist
3. **testing.md** - Test creation specialist
4. **docs-vision.md** - Documentation and quality agent

Use templates from Part 6, customizing:
- Code standards based on detected style
- Anti-patterns based on detected patterns

### Step 3.5: Generate Skills

For each detected framework, generate a skill file:

```bash
# For each detected framework
mkdir -p .claude/skills/{framework}
# Write SKILL.md using framework template from Part 7
```

Frameworks to check:
- Python: litestar, fastapi, flask, django, pytest
- JS: react, vue, svelte, angular, vite, inertia, vitest

### Step 3.6: Generate Settings

Create `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__context7__resolve-library-id",
      "mcp__context7__get-library-docs",
      "mcp__sequential-thinking__sequentialthinking",
      "mcp__zen__planner",
      "mcp__zen__thinkdeep",
      "mcp__zen__debug",
      "mcp__zen__analyze",
      "WebSearch",
      "{BUILD_COMMANDS}",
      "{TEST_COMMANDS}",
      "{LINT_COMMANDS}",
      "Bash(git:*)",
      "Bash(gh:*)"
    ]
  }
}
```

Customize `{BUILD_COMMANDS}`, `{TEST_COMMANDS}`, `{LINT_COMMANDS}` based on detection.

### Step 3.7: Generate Specs Guides

Create initial guide files:

1. **architecture.md** - Project structure documentation
2. **code-style.md** - Code conventions based on detection
3. **testing.md** - Testing patterns
4. **quality-gates.yaml** - Quality checks
5. **development-workflow.md** - How to work on this project

---

## Part 4: Alignment Mode

When existing bootstrap is detected, use this mode instead of fresh generation.

### Step 4.1: Inventory Existing Configuration

```bash
# List existing commands
ls .claude/commands/*.md 2>/dev/null

# List existing skills
ls -d .claude/skills/*/ 2>/dev/null

# List existing agents
ls .claude/agents/*.md 2>/dev/null

# Check CLAUDE.md version
head -5 CLAUDE.md 2>/dev/null | grep "Version"
```

### Step 4.2: Identify Missing Components

Compare existing vs expected:

**Core commands (must exist)**:
- prd.md
- implement.md
- test.md
- review.md
- explore.md
- fix-issue.md

**Core agents (must exist)**:
- prd.md
- expert.md
- testing.md
- docs-vision.md

**Framework skills (based on detection)**:
- Check if skill exists for each detected framework
- Flag missing skills for generation

### Step 4.3: Preserve Custom Content

Before updating any file:

1. Read existing content
2. Identify custom sections (not matching template markers)
3. Store custom content for preservation
4. Merge custom content into updated file

**Custom content markers**:
- Commands not in core list are custom
- Skills not in framework list are custom
- Sections marked `## Custom` are preserved

### Step 4.4: Update Outdated Patterns

Check for outdated patterns and offer to update:

```markdown
## Alignment Report

### New Components to Add
- [ ] Skill: {new detected framework}
- [ ] Command: {missing core command}

### Updates Available
- [ ] CLAUDE.md version {old} → {new}
- [ ] Command {name}: {change description}

### Custom Content Preserved
- Command: {custom command name}
- Skill: {custom skill name}

Proceed with updates? [Y/n]
```

### Step 4.5: Merge and Update

For each file to update:

1. Generate new content from template
2. Insert preserved custom content
3. Write merged file
4. Update version number

---

## Part 5: Verification

### Step 5.1: Validate Generated Files

```bash
# Check all expected files exist
test -f CLAUDE.md && echo "✓ CLAUDE.md"
test -d .claude/commands && echo "✓ .claude/commands/"
test -d .claude/agents && echo "✓ .claude/agents/"
test -d .claude/skills && echo "✓ .claude/skills/"
test -f .claude/settings.local.json && echo "✓ settings.local.json"
test -d specs/guides && echo "✓ specs/guides/"
test -d specs/active && echo "✓ specs/active/"

# Count generated files
echo "Commands: $(ls .claude/commands/*.md 2>/dev/null | wc -l)"
echo "Agents: $(ls .claude/agents/*.md 2>/dev/null | wc -l)"
echo "Skills: $(ls -d .claude/skills/*/ 2>/dev/null | wc -l)"
```

### Step 5.2: Summary Report

```markdown
## Bootstrap Complete ✓

### Generated Configuration

**CLAUDE.md**: Main AI instructions
- Tech Stack: {detected stack}
- Commands: {count}
- Skills: {count}

**Commands Created**:
- /prd - Create PRD for new feature
- /implement - Implement from PRD
- /test - Run comprehensive tests
- /review - Quality gate and archive
- /explore - Explore codebase
- /fix-issue - Fix GitHub issue

**Agents Created**:
- prd - PRD creation specialist
- expert - Implementation specialist
- testing - Test creation specialist
- docs-vision - Documentation agent

**Skills Created**:
{list of framework skills}

**Specs Structure**:
- specs/guides/ - Project documentation
- specs/active/ - Active workspaces
- specs/archive/ - Completed work

### Next Steps

1. Review generated CLAUDE.md
2. Customize settings.local.json permissions as needed
3. Run `/explore` to test configuration
4. Start development with `/prd [feature]`
```

---

## Part 6: Embedded Templates

### Template: CLAUDE.md

```markdown
# AI Agent Guidelines for {PROJECT_NAME}

**Version**: 1.0 | **Updated**: {DATE}

{PROJECT_DESCRIPTION}

---

## Quick Reference

### Technology Stack

| Backend | Frontend |
|---------|----------|
| {BACKEND_TECH} | {FRONTEND_TECH} |
| {BACKEND_TEST} | {FRONTEND_TEST} |
| {BACKEND_LINT} | {FRONTEND_LINT} |
| {BACKEND_PKG} | {FRONTEND_PKG} |

### Essential Commands

```bash
{INSTALL_CMD}    # Install all dependencies
{TEST_CMD}       # Run all tests
{LINT_CMD}       # Run linting
{FIX_CMD}        # Auto-format code
```

### Project Structure

```
{PROJECT_STRUCTURE}
```

---

## Code Standards (Critical)

### {PRIMARY_LANGUAGE}

| Rule | Standard |
|------|----------|
| Type hints | {TYPE_HINT_STYLE} |
| Docstrings | {DOCSTRING_STYLE} |
| Tests | {TEST_STYLE} |
| Line length | {LINE_LENGTH} characters |

{SECONDARY_LANGUAGE_SECTION}

---

## Available Skills

Framework-specific expertise in `.claude/skills/`:

{SKILLS_TABLE}

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/prd [feature]` | Create PRD for new feature |
| `/implement [slug]` | Implement from PRD |
| `/test [slug]` | Run comprehensive tests |
| `/review [slug]` | Quality gate and archive |
| `/explore [topic]` | Explore codebase |
| `/fix-issue [#]` | Fix GitHub issue |
| `/bootstrap` | Re-bootstrap (alignment mode) |

---

## Subagents

Invoke via Task tool with `subagent_type`:

| Agent | Mission |
|-------|---------|
| `prd` | Create PRDs and task breakdowns |
| `expert` | Implement production code |
| `testing` | Create 90%+ coverage test suites |
| `docs-vision` | Quality gates and archival |

### Example Invocation

```python
Task(
    description="Create PRD",
    prompt="Create PRD for: [feature]",
    subagent_type="prd",
    model="sonnet"
)
```

---

## Development Workflow

### For New Features

1. **PRD**: `/prd [feature]` or `subagent_type="prd"`
2. **Implement**: `/implement [slug]` or `subagent_type="expert"`
3. **Test**: Auto-invoked or `/test [slug]`
4. **Review**: Auto-invoked or `/review [slug]`

### For Bug Fixes

1. `/fix-issue [number]`
2. Or manual: Search → Fix → Test → Commit

### Quality Gates

All code must pass:
- [ ] `{TEST_CMD}` passes
- [ ] `{LINT_CMD}` passes
- [ ] 90%+ coverage for modified modules
- [ ] No anti-patterns

---

## MCP Tools

### Context7 (Library Docs)

```python
mcp__context7__resolve-library-id(libraryName="{PRIMARY_FRAMEWORK}")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="{CONTEXT7_ID}",
    topic="...",
    mode="code"
)
```

### Sequential Thinking

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: ...",
    thought_number=1,
    total_thoughts=10,
    next_thought_needed=True
)
```

---

## Anti-Patterns (Must Avoid)

{ANTI_PATTERNS_TABLE}
```

### Template: prd.md Command

```markdown
---
description: Create a Product Requirements Document for a new feature
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking
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

Use sequential thinking to thoroughly analyze:

1. What problem does this solve?
2. Who are the users/consumers?
3. What are the acceptance criteria?
4. What are the technical constraints?
5. What existing code will be affected?
6. What new code needs to be written?
7. What tests are needed?

## Phase 3: Research (if needed)

If the feature involves external libraries:

```python
mcp__context7__resolve-library-id(libraryName="...")
mcp__context7__get-library-docs(...)
```

For best practices:
```python
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
- `{path}` - {what changes}

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
```

### Template: implement.md Command

```markdown
---
description: Implement a feature from an existing PRD
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
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

## Phase 3: Implementation

Follow the task breakdown and implement each component:

### Code Standards
{CODE_STANDARDS_SECTION}

### As You Work
- Update `tasks.md` progress
- Update `recovery.md` with current state
- Run tests frequently: `{TEST_CMD}`
- Run linting: `{LINT_CMD}`

## Phase 4: Local Testing

Before completing implementation:

```bash
# Run tests
{TEST_CMD}

# Run linting
{LINT_CMD}
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
- [ ] All functions have type hints
- [ ] All public APIs have docstrings
- [ ] No anti-patterns
- [ ] Local tests pass
- [ ] Linting clean
```

### Template: test.md Command

```markdown
---
description: Run comprehensive tests for a feature
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Testing Workflow

Testing feature: **specs/active/$ARGUMENTS**

## Phase 1: Load Context

1. Read the PRD:
   - `specs/active/$ARGUMENTS/prd.md`
   - Identify acceptance criteria
   - Note testing requirements

2. Read existing tests:
   - Find related test files
   - Understand existing patterns

## Phase 2: Test Coverage Check

```bash
# Run tests with coverage
{TEST_COVERAGE_CMD}

# Check coverage for modified modules
{COVERAGE_CHECK_CMD}
```

## Phase 3: Create Missing Tests

For each acceptance criterion without tests:

1. Create unit tests
2. Create integration tests
3. Test edge cases

### Test Patterns
{TEST_PATTERNS_SECTION}

## Phase 4: Run Full Test Suite

```bash
# Run all tests
{TEST_CMD}

# Run linting
{LINT_CMD}
```

## Phase 5: Update Tasks

Update `specs/active/$ARGUMENTS/tasks.md`:
- Mark testing tasks complete
- Note coverage percentage
- Document any issues

## Testing Checklist

- [ ] All acceptance criteria have tests
- [ ] 90%+ coverage for modified modules
- [ ] Edge cases tested
- [ ] Integration tests pass
- [ ] No flaky tests
```

### Template: review.md Command

```markdown
---
description: Run quality gates and documentation review
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Review Workflow

Reviewing feature: **specs/active/$ARGUMENTS**

## Phase 1: Quality Gates

### Tests
```bash
{TEST_CMD}
```

### Linting
```bash
{LINT_CMD}
```

### Coverage
```bash
{COVERAGE_CMD}
```

## Phase 2: Anti-Pattern Scan

Check for anti-patterns:

```bash
{ANTI_PATTERN_CHECKS}
```

## Phase 3: Documentation Check

- [ ] All public APIs have docstrings
- [ ] Complex logic has comments
- [ ] README updated if needed
- [ ] specs/guides/ updated if new patterns

## Phase 4: Archive Workspace

If all gates pass:

```bash
# Move to archive
mv specs/active/$ARGUMENTS specs/archive/

# Create archive summary
```

Create `specs/archive/$ARGUMENTS/ARCHIVED.md`:

```markdown
# Archived: {Feature Name}

**Completed**: {date}
**Duration**: {start to end}

## Summary
{What was implemented}

## Files Changed
{List of modified files}

## Tests Added
{List of new tests}

## Lessons Learned
{Any insights for future work}
```

## Review Checklist

- [ ] All tests pass
- [ ] All linting clean
- [ ] 90%+ coverage
- [ ] No anti-patterns
- [ ] Documentation complete
- [ ] Workspace archived
```

### Template: explore.md Command

```markdown
---
description: Explore and understand the codebase structure
allowed-tools: Glob, Grep, Read, Bash
---

# Codebase Exploration

Exploring: **$ARGUMENTS**

## Project Structure

Use Glob and Grep to explore:

```
# Find files matching topic
Glob(pattern="**/*{topic}*")

# Search for patterns
Grep(pattern="{topic}", path="src/")

# Find classes
Grep(pattern="class.*{topic}", path="src/")

# Find functions
Grep(pattern="def.*{topic}", path="src/")
```

## Common Patterns

After finding relevant code, explain:

1. How it's structured
2. How components interact
3. Key design patterns used
4. Entry points and data flow
```

### Template: fix-issue.md Command

```markdown
---
description: Fix a GitHub issue
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Fix GitHub Issue

Fixing issue: **#$ARGUMENTS**

## Phase 1: Understand the Issue

```bash
# Fetch issue details
gh issue view $ARGUMENTS
```

## Phase 2: Find Related Code

Search for affected code:

```
Grep(pattern="{keywords from issue}")
Glob(pattern="**/*{affected area}*")
```

## Phase 3: Implement Fix

1. Read the affected files
2. Understand the problem
3. Implement the fix
4. Follow project code standards

## Phase 4: Test the Fix

```bash
# Run related tests
{TEST_CMD}

# Run linting
{LINT_CMD}
```

## Phase 5: Create PR

```bash
# Commit with issue reference
git add .
git commit -m "fix: {description}

Fixes #$ARGUMENTS"

# Create PR
gh pr create --title "Fix #{issue}: {title}" --body "Fixes #$ARGUMENTS

## Changes
- {change 1}
- {change 2}

## Testing
- {how tested}"
```
```

### Template: Expert Agent

```markdown
---
name: expert
description: Implementation specialist. Writes production-quality code following project standards. Use for implementing features from PRDs.
tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
model: sonnet
---

# Expert Agent

**Mission**: Write production-quality code that meets acceptance criteria and project standards.

## Project Standards

{CODE_STANDARDS_TABLE}

## Workflow

### 1. Load PRD and Tasks

```
Read("specs/active/{slug}/prd.md")
Read("specs/active/{slug}/tasks.md")
```

### 2. Research Codebase

```
Read("CLAUDE.md")
Grep(pattern="...", path="src/")
Glob(pattern="src/**/*")
```

### 3. Research Libraries (if needed)

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="...",
    topic="...",
    mode="code"
)
```

### 4. Implement

Follow code standards from CLAUDE.md.

### 5. Test Locally

```bash
{TEST_CMD} && {LINT_CMD}
```

### 6. Update Progress

Edit `tasks.md` and `recovery.md` with current state.

### 7. Auto-Invoke Testing Agent

After implementation complete:

```
Task(
    description="Run comprehensive tests",
    prompt="Test specs/active/{slug}",
    subagent_type="testing",
    model="sonnet"
)
```

## Anti-Patterns to Avoid

{ANTI_PATTERNS_LIST}
```

### Template: PRD Agent

```markdown
---
name: prd
description: Strategic planning specialist. Creates comprehensive PRDs, task breakdowns, and requirement structures. Use for new features requiring planning.
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking
model: sonnet
---

# PRD Agent

**Mission**: Create comprehensive, research-grounded Product Requirements Documents.

## Workflow

### 1. Understand Request

Read project context and search for related code.

### 2. Deep Analysis

Use Sequential Thinking for comprehensive analysis:

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: Analyze requirements",
    thought_number=1,
    total_thoughts=15,
    next_thought_needed=True
)
```

### 3. Research

Use Context7 for library documentation.
Use WebSearch for best practices.

### 4. Create Workspace

```bash
mkdir -p specs/active/{slug}/research
mkdir -p specs/active/{slug}/tmp
```

### 5. Write PRD

Create comprehensive PRD with:
- Problem statement
- Acceptance criteria
- Technical approach
- Testing strategy

### 6. Create Tasks

Break down into actionable tasks.

### 7. Create Recovery Guide

Enable session resumption.

## Quality Checks

- [ ] PRD is 800+ words
- [ ] Research is 500+ words
- [ ] Acceptance criteria are specific
- [ ] Tasks are measurable
- [ ] Recovery guide is complete
```

### Template: Testing Agent

```markdown
---
name: testing
description: Test creation specialist. Creates comprehensive test suites with 90%+ coverage. Use after implementation is complete.
tools: Read, Write, Edit, Glob, Grep, Bash, mcp__context7__get-library-docs
model: sonnet
---

# Testing Agent

**Mission**: Create comprehensive tests achieving 90%+ coverage.

## Workflow

### 1. Load Context

Read PRD and identify acceptance criteria.

### 2. Find Existing Tests

```
Glob(pattern="tests/**/*test*.py")
```

### 3. Check Coverage

```bash
{COVERAGE_CMD}
```

### 4. Create Tests

For each acceptance criterion:
- Unit tests
- Integration tests
- Edge case tests

### 5. Run Tests

```bash
{TEST_CMD}
```

### 6. Verify Coverage

```bash
{COVERAGE_CHECK_CMD}
```

## Test Standards

{TEST_STANDARDS}

## Coverage Target

- 90%+ for modified modules
- All acceptance criteria tested
- Edge cases covered
```

### Template: Docs-Vision Agent

```markdown
---
name: docs-vision
description: Documentation and quality gate specialist. Runs quality checks, captures knowledge, and archives completed work. Use after testing passes.
tools: Read, Write, Edit, Glob, Grep, Bash
model: haiku
---

# Docs-Vision Agent

**Mission**: Ensure quality gates pass and archive completed work.

## Workflow

### 1. Run Quality Gates

```bash
{TEST_CMD}
{LINT_CMD}
{TYPE_CHECK_CMD}
```

### 2. Check Anti-Patterns

```bash
{ANTI_PATTERN_CHECKS}
```

### 3. Verify Documentation

- All public APIs documented
- Complex logic commented
- Guides updated if needed

### 4. Archive Workspace

```bash
mv specs/active/{slug} specs/archive/
```

### 5. Create Archive Summary

Write ARCHIVED.md with completion summary.

## Quality Gates

- [ ] Tests pass
- [ ] Linting clean
- [ ] Coverage 90%+
- [ ] No anti-patterns
- [ ] Docs complete
```

### Template: settings.local.json

```json
{
  "permissions": {
    "allow": [
      "mcp__context7__resolve-library-id",
      "mcp__context7__get-library-docs",
      "mcp__sequential-thinking__sequentialthinking",
      "mcp__zen__planner",
      "mcp__zen__thinkdeep",
      "mcp__zen__debug",
      "mcp__zen__analyze",
      "mcp__zen__chat",
      "WebSearch",
      "Bash(git:*)",
      "Bash(gh:*)",
      "Bash(mkdir:*)",
      "Bash(mv:*)",
      "Bash(rm:*)",
      "Bash(test:*)",
      "Bash(ls:*)",
      "{CUSTOM_BUILD_PERMISSIONS}"
    ]
  }
}
```

### Template: architecture.md Guide

```markdown
# Architecture Guide

## Overview

{PROJECT_DESCRIPTION}

## Project Structure

```
{PROJECT_STRUCTURE}
```

## Key Components

{COMPONENT_DESCRIPTIONS}

## Design Patterns

{DETECTED_PATTERNS}

## Data Flow

{DATA_FLOW_DESCRIPTION}
```

### Template: code-style.md Guide

```markdown
# Code Style Guide

## {PRIMARY_LANGUAGE}

### Type Hints
{TYPE_HINT_RULES}

### Docstrings
{DOCSTRING_RULES}

### Testing
{TEST_RULES}

### Formatting
{FORMAT_RULES}

## {SECONDARY_LANGUAGE}

{SECONDARY_RULES}

## Anti-Patterns

{ANTI_PATTERN_RULES}
```

### Template: quality-gates.yaml

```yaml
gates:
  tests:
    command: "{TEST_CMD}"
    required: true
  lint:
    command: "{LINT_CMD}"
    required: true
  coverage:
    minimum: 90
    required: true
  anti_patterns:
    - "{ANTI_PATTERN_1}"
    - "{ANTI_PATTERN_2}"
```

---

## Part 7: Framework Knowledge Base

### Python: Litestar

```markdown
---
name: litestar
description: Expert knowledge for Litestar Python web framework. Use when working with Litestar routes, plugins, middleware, dependency injection, or configuration.
---

# Litestar Framework Skill

## Quick Reference

### Plugin Development

```python
from litestar.plugins import InitPluginProtocol
from litestar import Litestar

class MyPlugin(InitPluginProtocol):
    def __init__(self, config: MyConfig) -> None:
        self.config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Modify app config during initialization."""
        app_config.state["my_plugin"] = self
        return app_config
```

### Route Handlers

```python
from litestar import get, post, Controller
from litestar.di import Provide

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    return await fetch_item(item_id)

class ItemController(Controller):
    path = "/items"
    dependencies = {"service": Provide(get_service)}

    @get("/")
    async def list_items(self, service: ItemService) -> list[Item]:
        return await service.list_all()
```

### Dependency Injection

```python
from litestar.di import Provide

def get_db_session(state: State) -> AsyncSession:
    return state.db_session

@get("/", dependencies={"session": Provide(get_db_session)})
async def handler(session: AsyncSession) -> Response:
    ...
```

### Middleware

```python
from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send

class MyMiddleware(AbstractMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Pre-processing
        await self.app(scope, receive, send)
        # Post-processing
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="plugins middleware dependency-injection",
    mode="code"
)
```
```

### Python: FastAPI

```markdown
---
name: fastapi
description: Expert knowledge for FastAPI web framework. Use when building FastAPI routes, dependencies, or middleware.
---

# FastAPI Framework Skill

## Quick Reference

### Route Handlers

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: int) -> Item:
    return await fetch_item(item_id)

@app.post("/items")
async def create_item(item: ItemCreate) -> Item:
    return await save_item(item)
```

### Dependencies

```python
from fastapi import Depends

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items")
async def list_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### Middleware

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="dependencies middleware",
    mode="code"
)
```
```

### Python: pytest

```markdown
---
name: pytest
description: Expert knowledge for pytest testing framework. Use when writing tests, fixtures, or test configuration.
---

# pytest Testing Skill

## Quick Reference

### Basic Tests

```python
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_exception():
    with pytest.raises(ValueError):
        raise ValueError("test")
```

### Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app) as client:
        yield client

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

### Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/pytest-dev/pytest",
    topic="fixtures parametrize async",
    mode="code"
)
```
```

### JavaScript: React

```markdown
---
name: react
description: Expert knowledge for React 18+ development with TypeScript. Use when building React components, managing state, or integrating with APIs.
---

# React Framework Skill

## Quick Reference

### Component Patterns

```tsx
import { useState, useEffect } from 'react';

interface Props {
  title: string;
  items: Item[];
  onSelect?: (item: Item) => void;
}

export function ItemList({ title, items, onSelect }: Props) {
  const [selected, setSelected] = useState<Item | null>(null);

  const handleSelect = (item: Item) => {
    setSelected(item);
    onSelect?.(item);
  };

  return (
    <div>
      <h2>{title}</h2>
      <ul>
        {items.map(item => (
          <li key={item.id} onClick={() => handleSelect(item)}>
            {item.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Custom Hooks

```tsx
export function useItems() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/items')
      .then(res => res.json())
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return { items, loading };
}
```

### Vite + React Setup

```tsx
// main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/facebook/react",
    topic="hooks components typescript",
    mode="code"
)
```
```

### JavaScript: Vue

```markdown
---
name: vue
description: Expert knowledge for Vue 3 development with Composition API and TypeScript. Use when building Vue components or composables.
---

# Vue 3 Framework Skill

## Quick Reference

### Component with Composition API

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface Props {
  title: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  select: [item: Item];
}>();

const items = ref<Item[]>([]);
const loading = ref(true);

const filteredItems = computed(() =>
  items.value.filter(i => i.active)
);

onMounted(async () => {
  items.value = await fetchItems();
  loading.value = false;
});

function handleSelect(item: Item) {
  emit('select', item);
}
</script>

<template>
  <div>
    <h2>{{ title }}</h2>
    <ul v-if="!loading">
      <li
        v-for="item in filteredItems"
        :key="item.id"
        @click="handleSelect(item)"
      >
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>
```

### Composables

```ts
// composables/useItems.ts
import { ref, onMounted } from 'vue';

export function useItems() {
  const items = ref<Item[]>([]);
  const loading = ref(true);

  onMounted(async () => {
    items.value = await fetch('/api/items').then(r => r.json());
    loading.value = false;
  });

  return { items, loading };
}
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vuejs/core",
    topic="composition-api composables typescript",
    mode="code"
)
```
```

### JavaScript: Svelte

```markdown
---
name: svelte
description: Expert knowledge for Svelte 5 development with runes. Use when building Svelte components or stores.
---

# Svelte 5 Framework Skill

## Quick Reference

### Component with Runes

```svelte
<script lang="ts">
  interface Props {
    title: string;
    items: Item[];
    onselect?: (item: Item) => void;
  }

  let { title, items, onselect }: Props = $props();

  let selected = $state<Item | null>(null);

  let filteredItems = $derived(items.filter(i => i.active));

  function handleSelect(item: Item) {
    selected = item;
    onselect?.(item);
  }
</script>

<div>
  <h2>{title}</h2>
  <ul>
    {#each filteredItems as item (item.id)}
      <li onclick={() => handleSelect(item)}>
        {item.name}
      </li>
    {/each}
  </ul>
</div>
```

### Stores

```ts
// stores.svelte.ts
class ItemStore {
  items = $state<Item[]>([]);
  loading = $state(true);

  async load() {
    this.items = await fetch('/api/items').then(r => r.json());
    this.loading = false;
  }
}

export const itemStore = new ItemStore();
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/sveltejs/svelte",
    topic="runes state effects",
    mode="code"
)
```
```

### JavaScript: Angular

```markdown
---
name: angular
description: Expert knowledge for Angular 18+ with signals. Use when building Angular components, services, or modules.
---

# Angular Framework Skill

## Quick Reference

### Component with Signals

```typescript
import { Component, signal, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-item-list',
  standalone: true,
  template: `
    <h2>{{ title() }}</h2>
    <ul>
      @for (item of filteredItems(); track item.id) {
        <li (click)="handleSelect(item)">{{ item.name }}</li>
      }
    </ul>
  `
})
export class ItemListComponent {
  title = input.required<string>();
  items = input<Item[]>([]);
  itemSelected = output<Item>();

  selected = signal<Item | null>(null);

  filteredItems = computed(() =>
    this.items().filter(i => i.active)
  );

  handleSelect(item: Item) {
    this.selected.set(item);
    this.itemSelected.emit(item);
  }
}
```

### Services

```typescript
import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private http = inject(HttpClient);

  items = signal<Item[]>([]);
  loading = signal(true);

  async loadItems() {
    this.items.set(await this.http.get<Item[]>('/api/items').toPromise());
    this.loading.set(false);
  }
}
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/angular/angular",
    topic="signals components services",
    mode="code"
)
```
```

### JavaScript: Vite

```markdown
---
name: vite
description: Expert knowledge for Vite build tool. Use when configuring Vite, creating plugins, or managing HMR.
---

# Vite Build Tool Skill

## Quick Reference

### Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  }
});
```

### Custom Plugin

```typescript
import type { Plugin } from 'vite';

export function myPlugin(): Plugin {
  return {
    name: 'my-plugin',
    configResolved(config) {
      console.log('Config resolved:', config);
    },
    transform(code, id) {
      if (id.endsWith('.special')) {
        return transformCode(code);
      }
    }
  };
}
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vitejs/vite",
    topic="configuration plugins",
    mode="code"
)
```
```

### JavaScript: Inertia.js

```markdown
---
name: inertia
description: Expert knowledge for Inertia.js with various frontend frameworks. Use when building SPAs with server-side routing.
---

# Inertia.js Integration Skill

## Quick Reference

### React Setup

```tsx
import { createInertiaApp } from '@inertiajs/react';
import { createRoot } from 'react-dom/client';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.tsx', { eager: true });
    return pages[`./pages/${name}.tsx`];
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />);
  },
});
```

### Vue Setup

```typescript
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.vue', { eager: true });
    return pages[`./pages/${name}.vue`];
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
```

### Page Component

```tsx
import { Head, Link, usePage } from '@inertiajs/react';

interface PageProps {
  items: Item[];
}

export default function ItemsPage({ items }: PageProps) {
  const { flash } = usePage().props;

  return (
    <>
      <Head title="Items" />
      {flash.success && <div>{flash.success}</div>}
      <ul>
        {items.map(item => (
          <li key={item.id}>
            <Link href={`/items/${item.id}`}>{item.name}</Link>
          </li>
        ))}
      </ul>
    </>
  );
}
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/inertiajs/inertia",
    topic="pages links forms",
    mode="code"
)
```
```

### JavaScript: Vitest

```markdown
---
name: vitest
description: Expert knowledge for Vitest testing framework. Use when writing tests for Vite-based projects.
---

# Vitest Testing Skill

## Quick Reference

### Basic Tests

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('Calculator', () => {
  it('adds numbers', () => {
    expect(1 + 1).toBe(2);
  });

  it('throws on invalid input', () => {
    expect(() => divide(1, 0)).toThrow('Division by zero');
  });
});
```

### Mocking

```typescript
import { vi, describe, it, expect } from 'vitest';

vi.mock('./api', () => ({
  fetchItems: vi.fn(() => Promise.resolve([{ id: 1 }]))
}));

describe('ItemService', () => {
  it('fetches items', async () => {
    const items = await service.getItems();
    expect(items).toHaveLength(1);
  });
});
```

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';

describe('Button', () => {
  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);

    await userEvent.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalled();
  });
});
```

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vitest-dev/vitest",
    topic="mocking testing-library",
    mode="code"
)
```
```

---

## Execution Instructions

Now execute this bootstrap:

1. **Run Preflight Checks** (Part 1)
2. **If fresh**: Run Detection (Part 2), then Generation (Part 3)
3. **If existing**: Run Alignment (Part 4)
4. **Run Verification** (Part 5)
5. **Report Results**

Use the embedded templates (Part 6) and framework knowledge (Part 7) to generate all files.

**Begin bootstrap now.**
