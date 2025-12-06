# PRD: Inertia Integration Fixes

## Overview
- **Slug**: inertia-integration-fixes
- **Created**: 2025-12-06
- **Status**: Draft

## Problem Statement

There are three related issues affecting the Inertia integration in litestar-vite:

### Issue 1: Flash Plugin Template Dependency
The official Litestar `FlashPlugin` requires a `TemplateConfig` with an initialized template engine. This makes it incompatible with SPA-only Inertia applications that don't use Jinja2 templates. Users who want flash messages in their Inertia SPA apps cannot use the official plugin.

**Who has this problem?** Developers building template-less Inertia SPAs who want flash message support.

### Issue 2: Vite Dev Server Index Page (Inertia/Hybrid Mode)
When running in `mode="inertia"` (which normalizes to `hybrid`), if a user accidentally navigates directly to the Vite dev server port (e.g., `localhost:5173`), they won't see any useful content because:
- The Vite server serves raw frontend files (or nothing at root)
- The Laravel Vite plugin shows a helpful dev-server-index.html that redirects users to the correct backend URL

**Who has this problem?** Developers confused about which port to use during development.

### Issue 3: ViteSPAHandler Not Initialized in Hybrid Mode
When using `mode="hybrid"` with `spa_mode=True` in InertiaConfig, the `ViteSPAHandler` is created but never initialized during app startup. This causes a 500 error when trying to render Inertia pages:
```
ImproperlyConfiguredException: ViteSPAHandler not initialized. Call initialize() during app startup.
```

**Root Cause Analysis:**
1. In `plugin.py` line 1811-1821: `_spa_handler` is created for mode="hybrid" (else branch)
2. In `plugin.py` line 2094-2097: `_spa_handler.initialize()` is called if handler exists and not initialized
3. The bug: For some setups (complex plugin architectures, tests), the lifespan hook may not run properly

**Who has this problem?** Users with complex Litestar applications using ApplicationCore, multiple plugins, etc.

## Goals
1. Create an Inertia-compatible flash message system that works without templates
2. Serve a helpful dev-server-index.html when users access Vite directly in hybrid/inertia modes
3. Ensure ViteSPAHandler is always properly initialized in hybrid mode

## Non-Goals
- Replacing the official Litestar FlashPlugin (we'll provide an alternative)
- Breaking backwards compatibility with existing Inertia setups
- Changing how flash messages work conceptually

## Acceptance Criteria

### Issue 1: Flash Messages
- [ ] Flash messages work in SPA-only Inertia apps (no Jinja2 templates required)
- [ ] Existing template-based flash message apps continue to work
- [ ] Flash messages are accessible via `props.flash` in all Inertia responses
- [ ] Can use `flash(request, "message", "category")` helper in route handlers
- [ ] API compatible with existing `get_shared_props()` flash extraction

### Issue 2: Dev Server Index Page
- [ ] Navigating to Vite dev server URL in hybrid/inertia mode shows dev-server-index.html
- [ ] The page displays the correct APP_URL to navigate to
- [ ] Page styling matches the existing dev-server-index.html design
- [ ] This only applies to `mode="hybrid"` or `mode="inertia"`

### Issue 3: ViteSPAHandler Initialization
- [ ] ViteSPAHandler is always initialized when `spa_mode=True` in InertiaConfig
- [ ] Works with complex plugin architectures (ApplicationCore, etc.)
- [ ] Works in test environments
- [ ] No double-initialization issues
- [ ] All existing tests pass

## Technical Approach

### Issue 1: Flash Messages for Inertia SPA

**Current State:**
- Litestar's `FlashPlugin` requires `TemplateConfig` with template engine
- `get_shared_props()` in `helpers.py` already extracts flash messages from session
- Flash messages are passed as `props["flash"]` in every Inertia response

**Solution: Integrate flash handling directly into InertiaPlugin**

The InertiaPlugin already handles flash messages via `get_shared_props()`. The issue is that users expect to use `flash()` helper like with the official plugin. We need to:

1. **Re-export flash helper**: Export the `flash()` function from `litestar_vite.inertia` that writes to session
2. **No template dependency**: Flash messages are serialized as JSON in Inertia responses, not rendered in templates
3. **Documentation**: Document that Inertia apps don't need FlashPlugin

```python
# In litestar_vite/inertia/__init__.py
from litestar_vite.inertia.helpers import flash

# Usage in route handlers:
from litestar_vite.inertia import flash

@post("/action")
async def action(request: Request) -> InertiaResponse:
    flash(request, "Success!", "success")
    return InertiaResponse(...)
```

**Implementation:**
- Add `flash()` function to `helpers.py` (if not already there)
- Export it from `litestar_vite.inertia.__init__.py`
- Verify `get_shared_props()` correctly extracts all flash messages

### Issue 2: Dev Server Index Page for Inertia Mode

**Current State:**
- The `dev-server-index.html` already exists in the JS package
- It's served when no index.html is found in SPA/SSR modes
- In hybrid mode, the Vite plugin doesn't serve this page at root

**Solution: Serve dev-server-index.html for inertia/hybrid modes**

The TypeScript Vite plugin needs to detect when it's in hybrid/inertia mode and serve the dev-server-index.html when users access the root path. This matches Laravel Vite plugin behavior.

**Implementation in `src/js/src/index.ts`:**
1. Read the `mode` from `.litestar.json` (already loaded as `pythonDefaults`)
2. If mode is "hybrid" or no index.html exists, serve `dev-server-index.html` at "/"
3. Replace `{{ APP_URL }}` placeholder with actual APP_URL from environment

```typescript
// In configureServer middleware
if (!indexPath && req.url === "/") {
  // mode="hybrid" has no SPA index.html, serve placeholder
  const placeholderPath = path.join(dirname(), "dev-server-index.html")
  const content = await fs.promises.readFile(placeholderPath, "utf-8")
  res.statusCode = 200
  res.setHeader("Content-Type", "text/html")
  res.end(content.replace(/{{ APP_URL }}/g, appUrl))
  return
}
```

**Note:** Looking at the current code, this is already partially implemented for `/index.html` but not for `/` in hybrid mode. We need to extend this.

### Issue 3: ViteSPAHandler Initialization Fix

**Current State:**
- `_spa_handler` is created in `on_app_init()` for mode="hybrid"
- `_spa_handler.initialize()` is an async method called in lifespan hook
- Some setups don't properly run the lifespan before first request
- `initialize()` uses `anyio.Path` for file reading (async I/O)

**Root Cause Analysis:**
The `initialize()` method is async only because it uses `anyio.Path` for file reading. However:
1. `to_asgi_response()` runs ON the event loop thread (even though it's sync)
2. Any blocking I/O there blocks ALL concurrent requests
3. `httpx.AsyncClient` constructor is synchronous - only methods are async

**Consensus Analysis (Gemini 2.5 Pro - FOR vs AGAINST portal pattern):**

We evaluated whether to use sqlspec's portal utilities for async-to-sync bridging:

| Option | FOR (9/10) | AGAINST (9/10) |
|--------|-----------|----------------|
| A) Portal pattern | Preserves async-first design, future-proofs library, battle-tested | Disproportionate complexity, ~300 lines for one-time read |
| B) Sync initialize() | - | Addresses root cause directly, microsecond blocking negligible |
| C) Fail fast | - | Explicit, forces correct setup |
| D) ThreadPoolExecutor | - | Middle ground if fallback needed |

**Key Insight from AGAINST perspective:** The use of `anyio.Path` is self-inflicted complexity. One-time file reads during initialization are a classic case where synchronous I/O is simpler and entirely appropriate, even in an async-first framework.

**Final Decision: Option B - Make `initialize()` synchronous**

The consensus revealed that the portal pattern would be architectural over-engineering for this use case:
- File reading is one-time at startup
- Performance impact is negligible (microseconds)
- Eliminates the need for any fallback logic
- Removes `anyio` dependency from spa.py
- Simplifies the codebase significantly

**Solution: Dual sync/async methods with lazy fallback**

**Naming Convention**: Methods with both async and sync versions MUST use `_async` and `_sync` suffixes.

1. **Rename existing async methods** - `initialize()` → `initialize_async()`, `_load_index_html()` → `_load_index_html_async()`
2. **Add sync versions** - `initialize_sync()` using `pathlib.Path`
3. **Add lazy init fallback** - If not initialized in `get_html_sync()`, call `initialize_sync()` with warning
4. **Fix auto-detection** - Ensure mode="hybrid" is set when InertiaConfig is provided

```python
# spa.py - Dual sync/async methods (following ViteAssetLoader pattern)
def initialize_sync(self, vite_url: str | None = None) -> None:
    """Initialize the handler (synchronous)."""
    if self._initialized:
        return

    if self._config.is_dev_mode and self._config.hot_reload:
        self._http_client = httpx.AsyncClient(...)
        self._http_client_sync = httpx.Client(...)
    else:
        self._load_index_html_sync()  # Sync with pathlib.Path

    self._initialized = True

async def initialize_async(self, vite_url: str | None = None) -> None:
    """Initialize the handler (asynchronous)."""
    if self._initialized:
        return
    # ... async version using anyio.Path

def get_html_sync(self, *, page_data=None, csrf_token=None) -> str:
    """Get HTML synchronously."""
    if not self._initialized:
        import logging
        logging.getLogger("litestar_vite").warning(
            "ViteSPAHandler lazy init triggered - lifespan may not have run"
        )
        self.initialize_sync()  # Safe - it's synchronous
    # ... rest of method
```

**Why NOT portal pattern:**
- Adds ~300 lines of vendored code for a one-time file read
- Background thread management complexity
- "Magic" fallback hides configuration issues
- Industry norm: sync I/O is appropriate for initialization

### Issue 4: Auto-detect mode="hybrid" when InertiaConfig is provided

**Problem:** Users shouldn't need to set `mode="hybrid"` explicitly when they provide `InertiaConfig`.

**Current State:**
The auto-detection logic in `_detect_mode()` ALREADY handles this:
```python
if inertia_enabled:
    if self.inertia.spa_mode:  # Explicit spa_mode=True
        return "hybrid"
    if any(path.exists() for path in self.candidate_index_html_paths()):
        return "hybrid"  # index.html found
    return "template"  # Jinja-based Inertia
```

**But there's a subtle issue:** In dev mode BEFORE first build, `index.html` might not exist yet. This causes mode to be set to `"template"` instead of `"hybrid"`.

**Solution: Default to hybrid for Inertia SPA apps**

When `InertiaConfig` is provided without an explicit `spa_mode=False`, assume hybrid mode:

```python
def _detect_mode(self) -> Literal["spa", "template", "htmx", "hybrid"]:
    if inertia_enabled:
        # If spa_mode is explicitly False, use template mode
        if self.inertia.spa_mode is False:  # Explicit False, not just falsy
            return "template"

        # Otherwise, default to hybrid for SPA-style Inertia
        # (index.html will be served by Vite dev server or built assets)
        return "hybrid"
```

This makes the following "just work":
```python
vite = ViteConfig(
    inertia=InertiaConfig(root_template="index.html"),
    # No need for mode="hybrid" - auto-detected!
)
```

## Affected Files

### Python
- `src/py/litestar_vite/inertia/__init__.py` - Export `flash` helper
- `src/py/litestar_vite/inertia/helpers.py` - Ensure `flash()` function exists and is correct
- `src/py/litestar_vite/spa.py` - Make `initialize()` synchronous, replace `anyio.Path` with `pathlib.Path`, add lazy init fallback
- `src/py/litestar_vite/config.py` - Fix `_detect_mode()` to default to hybrid when InertiaConfig present
- `src/py/litestar_vite/plugin.py` - Update lifespan to call sync `initialize()` (remove await)

### TypeScript
- `src/js/src/index.ts` - Serve dev-server-index.html at root for hybrid mode

### Tests
- New tests for flash message integration
- Tests for ViteSPAHandler initialization edge cases
- E2E tests for dev server index page in hybrid mode

## Testing Strategy

### Unit Tests
- Flash message storage and retrieval without templates
- ViteSPAHandler sync initialization
- ViteSPAHandler fallback initialization

### Integration Tests
- Full Inertia request with flash messages
- Complex plugin setup with ApplicationCore
- Hybrid mode with spa_mode=True

### E2E Tests
- Browser test: navigate to Vite port, verify redirect page
- Full Inertia flow with flash messages displayed

## Research Questions
- [x] How does Laravel Vite plugin handle dev server root access? (Shows dev-server-index.html)
- [x] What template dependencies does FlashPlugin have? (Requires TemplateConfig)
- [x] Where is flash() helper defined? (Need to add or export)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing flash apps | High | Keep backwards compatibility, don't require changes |
| Blocking I/O in sync init | Negligible | File read is one-time at startup, microseconds of blocking |
| Double initialization | Low | `is_initialized` guard prevents (already present) |
| Dev server index not matching mode | Low | Read mode from .litestar.json explicitly |
| Removing anyio from spa.py | Low | Only used for Path operations, pathlib is equivalent |
| Lazy init warning noise | Low | Only triggers if lifespan didn't run properly |

## Comprehensive Async/Sync Pattern Analysis

A full review of ALL async/sync bridging patterns in `src/py/litestar_vite/` was conducted.

### Patterns Found

| Pattern | Location | Status | Action |
|---------|----------|--------|--------|
| **InertiaPlugin.portal** | `inertia/plugin.py:49-56` | ✅ Keep | Efficient shared portal for DeferredProp async callables |
| **DeferredProp.render()** | `inertia/helpers.py:323-337` | ✅ Keep | Uses portal for async prop execution, fallback creates temp portal |
| **ViteAssetLoader** | `loader.py:315-358` | ✅ Model | Has BOTH `_async` and `_sync` methods - **correct pattern** |
| **ViteSPAHandler.initialize()** | `spa.py` | ❌ Bug | Only async, missing sync - **follow ViteAssetLoader pattern** |
| **plugin.py anyio usage** | `plugin.py:78, 893, 913` | ✅ Correct | WebSocket exception handling, task groups - proper async context |

### Key Distinction: Portal vs File I/O

The consensus revealed an important distinction:

1. **InertiaPlugin.portal** (KEEP):
   - Used for `DeferredProp` async callable execution (user-defined async functions)
   - Cannot be replaced with sync methods - user functions are inherently async
   - Shared portal is efficient (vs per-call overhead)
   - Industry standard pattern (like Django's `async_to_sync`)

2. **ViteSPAHandler.initialize()** (FIX):
   - Uses `anyio.Path` for simple file I/O - unnecessary complexity
   - Should follow `ViteAssetLoader` pattern with dual `_async`/`_sync` methods
   - File reading can use sync `pathlib.Path`

### Consensus Result (FOR 10/10 vs AGAINST 9/10)

| Aspect | FOR Portal | AGAINST Portal |
|--------|-----------|----------------|
| Efficiency | Shared portal avoids per-call overhead | Global state is anti-pattern |
| Consistency | - | ViteAssetLoader dual-method is cleaner |
| Scope | - | Consider request-scoped portal for future |

**Final Decision**:
- **ViteSPAHandler**: Follow ViteAssetLoader pattern (dual sync/async methods)
- **InertiaPlugin.portal**: Keep as-is for DeferredProp (different use case)
- **Future consideration**: Request-scoped portal for DeferredProp (not in this PRD)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-06 | Rejected portal pattern for ViteSPAHandler | Disproportionate complexity (~300 lines) for one-time file read |
| 2025-12-06 | Chose ViteAssetLoader pattern for ViteSPAHandler | Dual sync/async methods, addresses root cause, consistent with codebase |
| 2025-12-06 | Keep InertiaPlugin.portal | Different use case - executes user async callables, not simple file I/O |
| 2025-12-06 | Add lazy init with warning | Graceful fallback if lifespan doesn't run, logs warning for debugging |

## Implementation Order

1. **Issue 3 first**: Fix ViteSPAHandler initialization (highest impact, blocking issue)
2. **Issue 1 second**: Flash message integration (moderate effort, improves DX)
3. **Issue 2 third**: Dev server index page (lowest priority, nice-to-have)

## Related Links

- [Laravel Vite Plugin Issue #96](https://github.com/laravel/vite-plugin/issues/96) - Similar dev server warning issue
- [Litestar Flash Plugin Docs](https://docs.litestar.dev/2/usage/plugins/flash_messages.html)
