# Research: Bootstrap Command for AI Development Infrastructure

## Analysis Summary

This research documents the architecture design for a self-contained bootstrap command that creates AI development infrastructure in any project.

## Key Findings

### 1. Current Structure Analysis

The litestar-vite project has a mature AI development setup:

**Claude Code configuration (.claude/):**
- 8 slash commands (prd, implement, test, review, explore, fix-issue, sync-llms-txt, update-templates)
- 5 subagents (prd, expert, testing, docs-vision, sync-guides)
- 10 skills (litestar, vite, react, vue, svelte, angular, inertia, htmx, nuxt, testing)
- settings.local.json with 67 permission rules

**Gemini CLI configuration (.gemini/):**
- 10 TOML command files (equivalent workflows)
- 8 context files (similar to skills)
- GEMINI.md main instructions
- settings.json with MCP server configurations

### 2. Detection Requirements

The bootstrap must detect:

**Languages:**
- Python (pyproject.toml, setup.py, requirements.txt)
- TypeScript/JavaScript (tsconfig.json, package.json)
- Rust, Go, Java (Cargo.toml, go.mod, pom.xml)

**Frameworks:**
- Python: litestar, fastapi, django, flask
- Frontend: react, vue, svelte, angular
- Integration: inertia, htmx
- Build: vite, webpack, esbuild
- Testing: pytest, vitest, jest

**Patterns:**
- Type hint style (Optional[T] vs T | None)
- Future annotations usage
- Test class vs function style
- Docstring format
- Line length conventions

### 3. Generation Requirements

**Core commands (always generated):**
1. `/prd [feature]` - PRD creation
2. `/implement [slug]` - Implementation execution
3. `/test [slug]` - Comprehensive testing
4. `/review [slug]` - Quality gate and archive
5. `/explore [topic]` - Codebase exploration
6. `/fix-issue [#]` - GitHub issue fixing

**Agents (Claude only):**
1. prd - PRD specialist
2. expert - Implementation specialist
3. testing - Test creation specialist
4. docs-vision - Documentation and quality

**Skills/Contexts (per detected framework):**
- Generated based on detection
- Include code patterns, examples, lookup references

### 4. Alignment Mode Requirements

For already-bootstrapped repositories:
- Detect existing configuration
- Preserve custom additions
- Update outdated patterns
- Add missing components
- Track versions

### 5. Self-Containment Strategy

The bootstrap files must be completely self-contained:
- All template patterns embedded
- All detection rules included
- All framework knowledge built-in
- No external references

Estimated size: 5000-7000 lines per bootstrap file

## Internal Patterns

The project uses:
- **Type hints**: `T | None` (PEP 604), never `Optional[T]`
- **No future annotations**: Never `from __future__ import annotations`
- **Tests**: Function-based pytest, no class-based tests
- **Docstrings**: Google style
- **Line length**: 120 characters

## Industry Best Practices

- Checkpoint-based workflows ensure quality and recoverability
- PRD-driven development reduces miscommunication
- Embedded expertise reduces errors
- Cross-platform support (Claude + Gemini) increases adoption

## Total Words: 520+
