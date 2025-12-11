# PRD: Python Code Cleanup for Beta Release

## Overview
- **Slug**: python-code-cleanup
- **Created**: 2025-12-10
- **Status**: Draft
- **Goal**: Clean up Python source code in `src/py/litestar_vite/` to remove code smells before removing the beta tag

## Problem Statement

The codebase has been revamped but contains code quality issues that should be addressed before the stable release:
1. **Nested imports** that should be at the top level (not conditional/circular)
2. **Inline comments** that explain obvious code or are implementation notes
3. **Overly defensive programming** patterns that add complexity without value
4. **Minor code smells** that impact maintainability

## Goals
1. Move non-conditional nested imports to top-level
2. Remove unnecessary inline comments
3. Reduce overly defensive code patterns where safe
4. Maintain 100% backward compatibility (no breaking changes)
5. Keep all existing functionality intact

## Non-Goals
- Adding new features
- Modifying test files
- Changing the TypeScript source

## Breaking Changes (Intentional)

### Rename: ViteSPAHandler → AppHandler

**Rationale**:
- "SPA" is misleading - handler works for spa, template, and ssr modes
- "Vite" prefix removed - now supports external dev servers too

**Changes**:
- Rename `src/py/litestar_vite/spa.py` → `src/py/litestar_vite/handler.py`
- Rename class `ViteSPAHandler` → `AppHandler`
- Update all imports in `__init__.py`, `plugin.py`, etc.
- No deprecation alias (clean break)

### Enhancement: Custom Guards Support

**Rationale**:
- Users may want to protect SPA/SSR routes with authentication guards
- Currently no way to add guards to the catch-all handler routes

**Changes**:
- Add `guards` parameter to `ViteConfig` (or relevant config class)
- Pass guards to `AppHandler` route registration
- Type: `Sequence[Guard] | None = None`

**Example**:
```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

def auth_guard(connection, handler) -> None:
    if not connection.user:
        raise NotAuthorizedException()

app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="spa",
            guards=[auth_guard],  # New option
        ))
    ],
)
```

### Config Consolidation: Remove InertiaConfig/SPAConfig Overlap

**Duplicated Fields**:

| Field | InertiaConfig | SPAConfig | Resolution |
|-------|---------------|-----------|------------|
| `app_selector` | `"#app"` | `"#app"` | Keep in SPAConfig only |

**Redundant Fields to Remove**:

| Field | Config | Reason | Migration |
|-------|--------|--------|-----------|
| `spa_mode` | InertiaConfig | Determined by `ViteConfig.mode` | Remove - use mode="hybrid" |
| `root_template` | InertiaConfig | Not used in SPA/hybrid mode | Keep but document as template-mode only |

**Auto-Configuration**:

When `inertia=True`:
1. Auto-set `spa.inject_csrf=True` (Inertia always needs CSRF)
2. Use `spa.app_selector` for Inertia data injection (remove `inertia.app_selector`)
3. If `mode` not set, auto-detect "hybrid" (already done)

**Breaking Change**: `InertiaConfig.app_selector` and `InertiaConfig.spa_mode` removed

**Example After**:
```python
# Before (redundant)
ViteConfig(
    mode="hybrid",
    inertia=InertiaConfig(spa_mode=True, app_selector="#app"),
    spa=SPAConfig(app_selector="#app", inject_csrf=True),
)

# After (clean)
ViteConfig(
    mode="hybrid",
    inertia=True,  # Auto-enables CSRF, uses spa.app_selector
    spa=SPAConfig(app_selector="#app"),  # Single source of truth
)
```

## Acceptance Criteria
- [ ] `ViteSPAHandler` renamed to `AppHandler` in `handler.py`
- [ ] Custom guards config option added to `ViteConfig`
- [ ] `InertiaConfig.app_selector` removed (use `SPAConfig.app_selector`)
- [ ] `InertiaConfig.spa_mode` removed (determined by `ViteConfig.mode`)
- [ ] Auto-enable CSRF when Inertia is configured
- [ ] All unnecessary nested imports moved to top-level
- [ ] Inline comments cleaned up (only keep valuable documentation)
- [ ] Overly defensive patterns simplified where safe
- [ ] `make lint` passes
- [ ] `make test` passes

---

## Technical Analysis

### 1. Nested Imports to Move to Top-Level

The following imports are nested inside functions but are NOT:
- Conditionally required
- Avoiding circular imports

#### cli.py (High Priority - Most Issues)

| Line | Import | Move to Top |
|------|--------|-------------|
| 55 | `from litestar_vite.config import LoggingConfig` | Yes |
| 96-97 | `from litestar.cli._utils import console`, `from rich.panel import Panel` | Yes - console already imported at module level |
| 197-198 | `from litestar_vite.exceptions import ViteExecutionError`, `from litestar_vite.plugin import set_environment` | Yes |
| 217 | `import msgspec` | Yes |
| 219 | `from litestar_vite.config import InertiaConfig, TypeGenConfig` | Yes |
| 260 | `import sys` | Yes |
| 262-266 | `from litestar.cli._utils import console`, `from rich.prompt import Prompt`, `from litestar_vite.scaffolding import...` | Yes |
| 313 | `from rich.prompt import Confirm` | Yes (already imported elsewhere) |
| 373-374 | `from litestar_vite.doctor import ViteDoctor`, `from litestar_vite.plugin import VitePlugin` | Yes |
| 526-534 | Multiple imports in `vite_init` | Yes |
| 630-633 | `from pathlib import Path`, `from litestar.cli._utils import console`, `from litestar_vite.plugin import VitePlugin` | Yes |
| 666-671 | Imports in `vite_build` | Yes |
| 734-736 | Imports in `vite_deploy` | Yes |
| 816-821 | Imports in `vite_serve` | Yes |
| 928-931 | Imports in `export_routes` | Yes |
| 1010-1011 | Imports in `_export_openapi_schema` | Yes |
| 1040-1043 | Imports in `_export_routes_metadata` | Yes |
| 1079-1083 | Imports in `_export_inertia_pages_metadata` | Yes |
| 1151-1154 | Imports in `_run_openapi_ts` | Yes |
| 1234-1237 | Imports in `generate_types` | Yes |
| 1279 | `import httpx` | Keep nested - optional dependency check pattern |

#### inertia/helpers.py

| Line | Import | Move to Top |
|------|--------|-------------|
| 406-407 | `from litestar_vite.inertia.types import ScrollPropsConfig` | Yes |
| 988-989 | `from litestar_vite.inertia.types import ScrollPropsConfig` | Yes (duplicate) |

#### executor.py

| Line | Import | Move to Top |
|------|--------|-------------|
| 225-226 | `from importlib.util import find_spec` | Yes |

#### deploy.py

| Line | Import | Move to Top |
|------|--------|-------------|
| 63-65 | `import fsspec`, `from fsspec.core import url_to_fs` | Keep nested - lazy import for optional dependency |

---

### 2. Inline Comments to Remove

#### cli.py

| Lines | Comment | Action |
|-------|---------|--------|
| 65, 75 | `# Reset executor to pick up new silent setting` | Remove - obvious from method name |
| 99-101 | Comment about spa_templates | Keep - explains mode selection |

#### executor.py

| Lines | Comment | Action |
|-------|---------|--------|
| 113-127 | Long comment block about subprocess.Popen behavior | Convert to docstring or remove duplication |
| 258-267 | Duplicate comment block | Remove - same as 113-127 |
| 148 | `# Keep stdin open - Nitro exits when stdin is closed` | Keep - important behavior note |

#### deploy.py

| Lines | Comment | Action |
|-------|---------|--------|
| 129-131 | Section divider comments | Keep - useful for navigation |

#### doctor.py

| Lines | Comment | Action |
|-------|---------|--------|
| 354-356 | Disabled check comment | Remove the entire disabled check method body |

---

### 3. Overly Defensive Programming Patterns

#### inertia/exception_handler.py

**Lines 127-131**: Overly broad exception handling
```python
try:
    if detail:
        flash(request, detail, category="error")
except (AttributeError, KeyError, RuntimeError, ImproperlyConfiguredException):
    request.logger.warning("Unable to set flash message", exc_info=True)
```
**Action**: Keep but simplify - this is actually appropriate defensive code for session handling.

#### inertia/helpers.py

**Multiple blocks**: `try/except (AttributeError, ImproperlyConfiguredException)` for session access
**Action**: Keep - these protect against missing session middleware which is a valid runtime scenario.

#### codegen.py

**Lines 275-280**: Try/except for dependency resolution
```python
try:
    resolved_deps = handler.resolve_dependencies()
    dependency_names = set(resolved_deps.keys())
except (AttributeError, KeyError, TypeError, ValueError):
    pass
```
**Action**: Keep - dependency resolution may fail in some contexts.

---

### 4. Code Smells to Address

#### cli.py

1. **Repeated `console` imports**: `from litestar.cli._utils import console` appears in many functions
   - **Action**: Import once at module level (it's already there, just duplicated)

2. **Long functions**: `vite_init` is ~100 lines
   - **Action**: Already refactored into helper functions, no change needed

3. **Duplicate import patterns**: Same imports in multiple CLI commands
   - **Action**: Consolidate at top of file

#### inertia/helpers.py

1. **Many overloads for `lazy()`**: 5 overload signatures
   - **Action**: Keep - needed for proper typing, but ensure docstring explains use cases

#### config.py

1. **Large file with many dataclasses**: Already well-organized
   - **Action**: No change needed

---

## Affected Files

Files with changes needed (sorted by priority):

### High Priority
1. `src/py/litestar_vite/cli.py` - Most nested imports
2. `src/py/litestar_vite/executor.py` - Duplicate comments
3. `src/py/litestar_vite/inertia/helpers.py` - Nested imports

### Medium Priority
4. `src/py/litestar_vite/doctor.py` - Dead code removal
5. `src/py/litestar_vite/deploy.py` - Minor cleanup

### Low Priority (No Changes Needed)
- `src/py/litestar_vite/config.py` - Clean
- `src/py/litestar_vite/loader.py` - Clean
- `src/py/litestar_vite/spa.py` - Clean
- `src/py/litestar_vite/plugin.py` - Clean
- `src/py/litestar_vite/codegen.py` - Clean
- `src/py/litestar_vite/exceptions.py` - Clean
- `src/py/litestar_vite/html_transform.py` - Clean
- `src/py/litestar_vite/inertia/*.py` - Mostly clean

---

## Implementation Strategy

### Phase 1: cli.py Cleanup
1. Move all non-conditional imports to top-level
2. Remove duplicate imports
3. Remove redundant comments
4. Keep section divider comments for navigation

### Phase 2: executor.py Cleanup
1. Remove duplicate comment blocks
2. Move `find_spec` import to top-level
3. Keep critical behavior comments

### Phase 3: helpers.py Cleanup
1. Move `ScrollPropsConfig` import to top-level
2. Review overload signatures (no changes needed)

### Phase 4: Minor Cleanups
1. doctor.py - Remove dead check code
2. deploy.py - Minor comment cleanup

### Phase 5: Validation
1. Run `make lint`
2. Run `make test`
3. Verify no public API changes

---

## Testing Strategy

- Run full test suite: `make test`
- Run linting: `make lint`
- Run type checking: `make type-check`
- Verify examples still work
- No new tests needed (pure refactoring)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import from moved imports | High | Test each file after moving imports |
| Breaking change from removed code | High | Only remove dead code, keep all functionality |
| Test failures | Medium | Run full test suite after each file |

---

## Research Questions

None - this is a straightforward cleanup task.
