# PRD: AI Development Infrastructure Bootstrap Command

## Overview

- **Slug**: bootstrap
- **Created**: 2025-11-28
- **Status**: Draft

The Bootstrap Command is a self-contained meta-tool that creates complete AI development infrastructure for any software project. It analyzes a codebase to detect languages, frameworks, libraries, and coding patterns, then generates appropriate configurations for both Claude Code and Gemini CLI, including slash commands, skills/contexts, agents, and the entire PRD-driven development workflow.

The bootstrap command is unique in that it must be **completely self-contained** - it cannot reference external templates or repositories. All knowledge required to generate configurations for detected frameworks must be embedded within the bootstrap file itself. This enables users to copy just the bootstrap file into any project and run it to create the entire AI development infrastructure.

Additionally, the bootstrap supports an **alignment mode** for projects that have already been bootstrapped. When run in an existing project, it detects current configurations, preserves custom additions, and updates outdated patterns to match the latest available configuration standards.

## Problem Statement

Setting up AI-assisted development infrastructure is currently a manual, error-prone process. Developers must:

1. Manually create configuration directories and files
2. Write slash commands for common workflows (PRD, implement, test, review)
3. Create skill/context files for each framework in use
4. Configure agent definitions with appropriate tools and permissions
5. Set up the specs/ directory structure for PRD-driven development
6. Maintain consistency between Claude and Gemini configurations

This results in:
- Inconsistent configurations across projects
- Missing best practices and anti-patterns
- No standardized workflow for AI-assisted development
- Difficulty keeping configurations up-to-date
- Fragmented knowledge that must be recreated for each project

The Bootstrap Command solves this by automating the entire setup process with intelligent detection and generation.

## Goals

1. **Primary**: Create a single `/bootstrap` command that generates complete AI development infrastructure for any project
2. **Secondary**: Enable alignment mode to update existing bootstrapped projects to latest standards
3. **Tertiary**: Provide cross-platform support for both Claude Code and Gemini CLI

## Non-Goals

- Runtime code execution or project scaffolding (this creates configs, not application code)
- Integration with other AI tools beyond Claude and Gemini
- Automated testing of generated configurations
- Cloud synchronization of configurations

## Acceptance Criteria

### Core Functionality

- [ ] AC-1: Bootstrap detects primary language(s) from config files (package.json, pyproject.toml, Cargo.toml, go.mod)
- [ ] AC-2: Bootstrap detects frameworks from dependencies (litestar, react, vue, vite, pytest, etc.)
- [ ] AC-3: Bootstrap detects code style patterns (type hints, docstrings, test style) from code samples
- [ ] AC-4: Bootstrap generates CLAUDE.md with detected tech stack, commands, skills, and anti-patterns
- [ ] AC-5: Bootstrap generates GEMINI.md with equivalent information in Gemini format
- [ ] AC-6: Bootstrap generates 6 core slash commands (prd, implement, test, review, explore, fix-issue)
- [ ] AC-7: Bootstrap generates 4 subagent definitions (prd, expert, testing, docs-vision) for Claude
- [ ] AC-8: Bootstrap generates skills/contexts for each detected framework
- [ ] AC-9: Bootstrap creates specs/ directory structure with guides/active/archive
- [ ] AC-10: Bootstrap generates settings files with appropriate permissions

### Self-Containment

- [ ] AC-11: Claude bootstrap file (.claude/bootstrap.md) works without referencing external repos
- [ ] AC-12: Gemini bootstrap file (.gemini/bootstrap.md) works without referencing external repos
- [ ] AC-13: All template patterns and framework knowledge are embedded in bootstrap files
- [ ] AC-14: Bootstrap files are 5000-7000 lines containing all necessary information

### Alignment Mode

- [ ] AC-15: Bootstrap detects existing .claude/ and .gemini/ directories
- [ ] AC-16: Bootstrap preserves custom commands and skills added by users
- [ ] AC-17: Bootstrap adds missing core commands without overwriting existing
- [ ] AC-18: Bootstrap updates outdated command patterns with user confirmation
- [ ] AC-19: Bootstrap includes version tracking for upgrade detection

### Quality

- [ ] AC-20: Generated commands follow checkpoint-based workflow pattern
- [ ] AC-21: Generated skills include code examples, patterns, and Context7 lookup references
- [ ] AC-22: Generated anti-patterns match detected code style
- [ ] AC-23: All generated files pass format validation

## Technical Approach

### Architecture

The bootstrap command operates as a prompt-driven file generator. When invoked, the AI agent reads the bootstrap.md file which contains:

1. **Execution instructions** - Step-by-step workflow phases
2. **Detection rules** - How to identify technologies and patterns
3. **Generation templates** - Patterns for each output file type
4. **Framework knowledge** - Embedded expertise for detected frameworks
5. **Alignment rules** - How to merge with existing configurations

```
bootstrap.md
    |
    v
+-------------------+
|   Detection       |  Scan config files, dependencies, code samples
+-------------------+
    |
    v
+-------------------+
|   Generation      |  Create configs based on detections
+-------------------+
    |
    v
+-------------------+
|   Verification    |  Validate and summarize created files
+-------------------+
```

### Affected Files

**New files to create (templates embedded in bootstrap):**

For Claude (.claude/):
- `bootstrap.md` - The self-contained bootstrap command (NEW)

For Gemini (.gemini/):
- `bootstrap.md` - The self-contained bootstrap command (NEW)

**Files generated by bootstrap (on target projects):**

```
{project}/
├── CLAUDE.md                    # Main Claude instructions
├── .claude/
│   ├── commands/
│   │   ├── prd.md              # PRD creation command
│   │   ├── implement.md        # Implementation command
│   │   ├── test.md             # Testing command
│   │   ├── review.md           # Review command
│   │   ├── explore.md          # Exploration command
│   │   └── fix-issue.md        # Issue fixing command
│   ├── agents/
│   │   ├── prd.md              # PRD agent
│   │   ├── expert.md           # Implementation agent
│   │   ├── testing.md          # Testing agent
│   │   └── docs-vision.md      # Documentation agent
│   ├── skills/
│   │   └── {framework}/SKILL.md # Per-framework skill
│   └── settings.local.json      # Permissions
├── .gemini/
│   ├── commands/
│   │   ├── prd.toml            # PRD command
│   │   ├── implement.toml      # Implementation command
│   │   └── ...
│   ├── context/
│   │   └── {framework}.md      # Per-framework context
│   ├── GEMINI.md               # Main Gemini instructions
│   └── settings.json           # MCP servers config
└── specs/
    ├── guides/
    │   ├── architecture.md     # System architecture
    │   ├── code-style.md       # Code conventions
    │   ├── testing.md          # Testing patterns
    │   ├── quality-gates.yaml  # Quality checks
    │   └── development-workflow.md
    ├── active/                 # Active workspaces
    └── archive/                # Completed workspaces
```

### Implementation Approach

**Phase 1: Detection Engine**

The bootstrap first scans the project to build a detection profile:

```python
# Detection profile structure
detection_profile = {
    "languages": ["python", "typescript"],
    "python_frameworks": ["litestar", "pytest"],
    "js_frameworks": ["react", "vite", "vitest"],
    "build_system": "make",  # or "npm scripts"
    "test_command": "make test",
    "lint_command": "make lint",
    "code_style": {
        "type_hints": "pep604",  # T | None
        "docstrings": "google",
        "test_style": "function",
        "line_length": 120
    },
    "anti_patterns": [
        "Optional[T]",
        "from __future__ import annotations",
        "class TestFoo:"
    ]
}
```

**Phase 2: Template Generation**

Based on detections, the bootstrap generates files using embedded patterns:

```markdown
## Template: CLAUDE.md

# AI Agent Guidelines for {PROJECT_NAME}

**Version**: 1.0 | **Updated**: {DATE}

{PROJECT_DESCRIPTION}

---

## Quick Reference

### Technology Stack

| Backend | Frontend |
|---------|----------|
| {BACKEND_TECH} | {FRONTEND_TECH} |
...
```

**Phase 3: Framework Skill Generation**

For each detected framework, generate a skill file:

```markdown
## Template: {FRAMEWORK}/SKILL.md

---
name: {framework}
description: Expert knowledge for {Framework Name}. Use when {triggers}.
---

# {Framework Name} Skill

## Quick Reference
{FRAMEWORK_PATTERNS}

## Project-Specific Patterns
{DETECTED_CODE_STYLE}

## Context7 Lookup
{CONTEXT7_LIBRARY_ID}
```

### Code Samples

**Detection logic (embedded in bootstrap):**

```bash
# Language detection
test -f package.json && echo "nodejs"
test -f pyproject.toml && echo "python"
test -f Cargo.toml && echo "rust"

# Framework detection from package.json
grep '"react"' package.json && echo "react"
grep '"vue"' package.json && echo "vue"
grep '"svelte"' package.json && echo "svelte"

# Framework detection from pyproject.toml
grep 'litestar' pyproject.toml && echo "litestar"
grep 'fastapi' pyproject.toml && echo "fastapi"
grep 'pytest' pyproject.toml && echo "pytest"

# Code style detection
grep -r "Optional\[" src/ && echo "uses_optional"
grep -r "| None" src/ && echo "uses_pep604"
grep -r "from __future__ import annotations" src/ && echo "uses_future"
```

**Skill generation pattern:**

```python
def generate_skill(framework: str, code_style: dict) -> str:
    """Generate skill markdown for detected framework.

    Args:
        framework: Detected framework name.
        code_style: Detected code style patterns.

    Returns:
        Skill markdown content.
    """
    template = get_framework_template(framework)
    template = template.replace("{{TYPE_HINT_STYLE}}", code_style["type_hints"])
    template = template.replace("{{DOCSTRING_STYLE}}", code_style["docstrings"])
    return template
```

### Database Changes

None - this feature creates configuration files only.

## Testing Strategy

### Unit Tests

- Test framework detection from mock package.json files
- Test framework detection from mock pyproject.toml files
- Test code style detection from sample Python files
- Test code style detection from sample TypeScript files
- Test template variable substitution

### Integration Tests

- Test full bootstrap on a mock Python+React project
- Test full bootstrap on a mock Python-only project
- Test full bootstrap on a mock TypeScript-only project
- Test alignment mode with existing configurations
- Test preservation of custom additions during alignment

### Edge Cases

- Empty project (no config files): Should prompt user for manual input
- Monorepo structure: Should detect multiple tech stacks
- Mixed Python versions: Should detect version constraints
- No test framework: Should generate basic test command
- Conflicting patterns: Should ask user for preference

### Performance Requirements

- Bootstrap should complete in under 60 seconds for typical projects
- Detection phase should complete in under 10 seconds
- Generation phase should complete in under 30 seconds

## Security Considerations

- Bootstrap reads files but makes no network requests
- Generated permissions in settings files should follow least-privilege
- No secrets or credentials should be included in generated files
- Bootstrap should warn if generating in a public repository

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect framework detection | Medium | Use multiple signals (dependencies + file patterns) |
| Overwriting custom configurations | High | Alignment mode with preservation logic |
| Bootstrap file becomes too large | Medium | Organize with clear sections, use markdown folding |
| Framework knowledge becomes outdated | Medium | Version tracking, regular updates |
| Cross-platform compatibility | Low | Test on both Claude and Gemini before release |

## Dependencies

- External libraries: None (pure markdown/prompt based)
- Internal components: Existing command/skill patterns from litestar-vite
- Infrastructure: None

## References

- Architecture: [specs/guides/architecture.md](../../guides/architecture.md)
- Research: [specs/active/bootstrap/research/plan.md](./research/plan.md)
- Existing commands: [.claude/commands/](../../../.claude/commands/)
- Existing skills: [.claude/skills/](../../../.claude/skills/)
