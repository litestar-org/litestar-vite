# AI Agent Guidelines for litestar-vite

**Version**: 3.1 | **Updated**: 2026-01-04 | **Project Version**: 0.16.0

Seamless integration between [Litestar](https://litestar.dev/) Python framework and [Vite](https://vitejs.dev/) with [Inertia.js](https://inertiajs.com/) support.

---

## Quick Reference

### Technology Stack

| Backend | Frontend |
|---------|----------|
| Python 3.10+ | TypeScript |
| Litestar | Vite 6.x/7.x |
| pytest, pytest-asyncio | Vitest |
| Ruff | Biome |
| uv | npm |

### Essential Commands

```bash
make install       # Install all dependencies
make test          # Run all tests
make lint          # Run linting (pre-commit + type-check + slotscheck)
make fix           # Auto-format code
make coverage      # Test with coverage
make check-all     # Run all checks (lint + test + coverage)
make type-check    # Run mypy + pyright
make build         # Build Python + JS packages
make clean         # Clean temporary build artifacts
```

### Litestar Assets CLI (Critical)

**ALWAYS use `litestar assets` commands instead of npm/node directly!**

```bash
# Development
litestar assets install          # Install frontend packages (NOT npm install)
litestar assets serve            # Start Vite dev server (NOT npm run dev)
litestar run                     # Start Litestar backend

# Production
litestar assets build            # Build frontend assets (NOT npm run build)
litestar assets serve --production  # Run SSR production server (for SSR modes)
litestar run                     # Serve built assets via Litestar

# Utilities
litestar assets status           # Check Vite integration status
litestar assets doctor           # Diagnose configuration issues
litestar assets generate-types   # Generate TypeScript types from OpenAPI
litestar assets export-routes    # Export route metadata for type-safe routing
```

**Why this matters:**
- The Litestar CLI manages port allocation, environment variables, and process coordination
- Direct npm commands bypass the Python-JS integration layer
- Tests and examples MUST use these commands to validate the real developer experience

### Project Structure

```
src/py/litestar_vite/     # Python library
  ├── config/             # ViteConfig (PathConfig, RuntimeConfig, TypeGenConfig, etc.)
  ├── plugin/             # VitePlugin internals
  ├── handler/            # AppHandler (SPA/HTML serving)
  ├── loader.py           # ViteAssetLoader
  ├── html_transform.py   # HTML transformation functions
  ├── deploy.py           # CDN deployment
  ├── codegen/            # Route/type generation
  └── inertia/            # Inertia.js integration
      ├── plugin.py       # InertiaPlugin
      ├── response.py     # InertiaResponse (props flattening)
      ├── middleware.py   # InertiaMiddleware
      └── helpers.py      # share, lazy, defer, merge, flash, error, only, except_, clear_history, scroll_props
src/js/src/               # TypeScript library
  ├── index.ts            # Main Vite plugin
  ├── helpers/            # CSRF utilities, HTMX utilities (addDirective, registerHtmxExtension, setHtmxDebug, swapJson)
  └── inertia-helpers/    # resolvePageComponent, unwrapPageProps
examples/                 # Framework examples
specs/guides/             # Project standards
```

---

## Code Standards (Critical)

### Python

| Rule | Standard |
|------|----------|
| Type hints | PEP 604: `T \| None` |
| Future annotations | **NEVER** - no `from __future__ import annotations` |
| Docstrings | Google style |
| Line length | 120 characters |
| Tests | Function-based only (no `class Test...`) |

### TypeScript

- Biome for formatting/linting
- Strict mode enabled
- Vitest for testing

---

## Available Skills

Framework-specific expertise in `.claude/skills/`:

| Skill | Use For |
|-------|---------|
| `litestar` | Litestar plugins, middleware, DI |
| `vite` | Vite plugins, HMR, asset bundling |
| `react` | React components, hooks |
| `vue` | Vue 3 Composition API |
| `svelte` | Svelte 5 runes |
| `inertia` | Inertia.js protocol |
| `htmx` | HTMX hypermedia |
| `nuxt` | Nuxt 3 SSR/SPA |
| `angular` | Angular 18+ signals |
| `testing` | pytest/Vitest patterns |

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
| `/sync-llms-txt` | Sync LLM documentation |
| `/update-templates` | Audit framework templates |
| `/bootstrap` | Bootstrap new project setup |
| `/review-docs` | Comprehensive documentation review |

---

## Subagents

Invoke via Task tool with `subagent_type`:

| Agent | Mission |
|-------|---------|
| `prd` | Create PRDs and task breakdowns |
| `expert` | Implement production code |
| `testing` | Create 90%+ coverage test suites |
| `docs-vision` | Quality gates and archival |
| `sync-guides` | Sync documentation with code |

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
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] 90%+ coverage for modified modules
- [ ] No anti-patterns (Optional, future annotations, class tests)

---

## MCP Tools

### Context7 (Library Docs)

```python
mcp__context7__resolve-library-id(libraryName="litestar")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="plugins",
    mode="code"
)
```

### Zen MCP

- `mcp__zen__planner` - Multi-step planning
- `mcp__zen__thinkdeep` - Architectural analysis
- `mcp__zen__debug` - Systematic debugging
- `mcp__zen__analyze` - Code analysis
- `mcp__zen__consensus` - Multi-model decisions

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

## Detailed Guides

For comprehensive documentation, see:

- `specs/guides/architecture.md` - System design
- `specs/guides/code-style.md` - Coding conventions
- `specs/guides/testing.md` - Testing strategies
- `specs/guides/quality-gates.yaml` - Automated checks

---

## Anti-Patterns (Must Avoid)

| Pattern | Use Instead |
|---------|-------------|
| `from __future__ import annotations` | Explicit string annotations |
| `class TestFoo:` | Function-based pytest |
| `hasattr()`/`getattr()` | Type guards |
| Nested try/except | Flat error handling |
| Mutable defaults | `None` with conditional |
| `npm run dev/build` in tests | `litestar assets serve/build` |
| Direct Node.js commands | Litestar CLI commands |
