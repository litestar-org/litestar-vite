# PRD: Unified Console Logging

## Overview
- **Slug**: unified-console-logging
- **Created**: 2025-12-08
- **Status**: Draft

## Problem Statement

When starting a litestar-vite application, developers experience a chaotic mix of log outputs from multiple sources with inconsistent formatting, timestamps, and verbosity levels. The current output is difficult to parse and debug because:

1. **Multiple Output Sources**: Logs come from Python (Litestar/Granian), TypeScript (Vite plugin), and npm scripts - all with different formatting
2. **Interleaved Timestamps**: Structlog JSON timestamps mix with colorful Vite banners and unformatted npm output
3. **Full Absolute Paths**: TypeScript output shows full system paths (e.g., `/home/cody/code/litestar/litestar-fullstack-inertia/...`) when relative paths would be cleaner
4. **Inconsistent Status Indicators**: Python uses `✓ • ! x`, Vite uses `➜`, and npm has no indicators
5. **Banner Duplication**: Multiple startup banners appear (Litestar table + VITE banner + LITESTAR banner)
6. **Duplicate Messages**: "Vite proxy enabled" appears twice (once from Python middleware, once from Vite plugin)

### Current Output Sample (Problematic)
```
Vite proxy enabled (whitelist) at /static/vite-hmr   <-- Python
2025-12-08T03:14:35.732655Z [info] message='Starting granian'  <-- Structlog

> dev                                                 <-- npm (no prefix)
> vite

Vite proxy enabled (whitelist) at /static/vite-hmr   <-- Vite (duplicate!)
litestar-vite watching schema/routes: /home/cody/code/litestar/litestar-fullstack-inertia/...  <-- FULL PATH
litestar-vite generating TypeScript types...
litestar-vite openapi-ts config: openapi-ts.config.ts

  VITE v7.2.7  ready in 2446 ms                       <-- Vite banner

  LITESTAR 2.18.0                                     <-- Litestar plugin banner
  ➜  Index Mode: SPA
  ➜  Dev Server: http://localhost:41277
  ➜  Type Gen:   enabled → /home/cody/code/.../generated  <-- FULL PATH again
```

## Goals

1. **Consistent Log Format**: All log messages follow a unified format with optional timestamps
2. **Relative Paths**: TypeScript output uses paths relative to project root
3. **Unified Prefixes**: All log lines use consistent `[litestar-vite]` prefix style
4. **Deduplicated Messages**: Remove duplicate "Vite proxy enabled" and similar messages
5. **Single Startup Banner**: Consolidate startup information into one clean banner
6. **Configurable Verbosity**: Add log level control for developers who want less noise

## Non-Goals

- Replacing structlog for Python application logs (those are user-controlled)
- Modifying Granian/uvicorn internal logging
- Suppressing Vite's core startup messages entirely
- Creating a custom logging framework

## Acceptance Criteria

- [ ] TypeScript plugin uses `path.relative()` for all output paths
- [ ] All litestar-vite TypeScript messages use consistent `[litestar-vite]` prefix
- [ ] Python `_log_info`, `_log_success` functions use same format as TypeScript
- [ ] Duplicate "Vite proxy enabled" message eliminated
- [ ] Single consolidated startup banner (choose Python or TypeScript, not both)
- [ ] Configuration option for verbose/quiet logging modes
- [ ] All paths in output are relative to project root

## Technical Approach

### Architecture

The logging system touches four distinct output sources:

| Source | Location | Format | Changes Needed |
|--------|----------|--------|----------------|
| Python plugin | `src/py/litestar_vite/plugin.py` | Rich console with `✓•!x` | Align format, add prefix |
| TypeScript plugin | `src/js/src/index.ts` | `resolvedConfig.logger.info()` | Use relative paths, unify prefix |
| Astro/Nuxt/SvelteKit plugins | `src/js/src/{astro,nuxt,sveltekit}.ts` | `console.log()` | Use relative paths, unify prefix |
| npm scripts | (external) | raw stdout | Cannot control directly |

### Affected Files

#### Python Side
- `src/py/litestar_vite/plugin.py`:
  - `_log_success()` - Add `[litestar-vite]` prefix
  - `_log_info()` - Add `[litestar-vite]` prefix
  - `_log_warn()` - Add `[litestar-vite]` prefix
  - `_log_fail()` - Add `[litestar-vite]` prefix
  - `_fmt_path()` - Ensure relative paths
  - Remove duplicate "Vite proxy enabled" from middleware startup

#### TypeScript Side
- `src/js/src/index.ts`:
  - Lines 628-694: Startup banner - consolidate/remove (let Python handle it)
  - Lines 1540-1600: Type generation logging - use relative paths
  - Lines 1650-1660: Watching paths logging - use relative paths
  - Add helper: `formatPath(absolutePath: string): string` returning relative

- `src/js/src/astro.ts`:
  - Lines 474-553: Type generation logging - use relative paths

- `src/js/src/nuxt.ts`:
  - Lines 337-347, 511-590: Logging - use relative paths

- `src/js/src/sveltekit.ts`:
  - Lines 393-402, similar sections - use relative paths

### Proposed Log Format

```
[litestar-vite] ✓ Types exported → resources/lib/generated/routes.json
[litestar-vite] • Watching: openapi.json, routes.json
[litestar-vite] • Starting Vite dev server (HMR enabled)
[litestar-vite] • Proxy target: http://127.0.0.1:41277
```

Key characteristics:
- Prefix: `[litestar-vite]` (consistent across Python and TypeScript)
- Status icons: `✓` (success), `•` (info), `!` (warning), `✗` (error)
- Relative paths only
- No timestamps (let structlog handle that for application logs)

### Startup Banner Strategy

**Option A (Recommended)**: Let TypeScript handle the fancy banner, Python handles operational logs

TypeScript outputs on server ready:
```
  LITESTAR 2.18.0 + VITE 7.2.7

  ➜  Index Mode: SPA (resources/index.html)
  ➜  App URL:    http://localhost:8088 ✓
  ➜  Dev Server: http://localhost:41277
  ➜  Type Gen:   enabled → resources/lib/generated/
```

Python outputs during startup:
```
[litestar-vite] • Applied environment variables
[litestar-vite] ✓ Types exported → routes.json
[litestar-vite] • Vite proxy at /static/vite-hmr
[litestar-vite] ✓ Dev server started
```

### Configuration via .litestar.json Bridge

The existing `BridgeSchema` (`.litestar.json`) already passes config from Python to TypeScript. Extend it to include logging settings:

```python
# Python ViteConfig (config.py)
class LoggingConfig(msgspec.Struct):
    """Logging configuration shared between Python and TypeScript."""
    level: Literal["quiet", "normal", "verbose"] = "normal"
    show_paths_absolute: bool = False  # False = relative paths (preferred)
    suppress_npm_output: bool = True   # Hide "> dev" / "> vite" echo
    suppress_vite_banner: bool = False # Hide VITE v7.2.7 banner
    timestamps: bool = False           # Add timestamps to litestar-vite logs
```

```typescript
// TypeScript BridgeSchema (index.ts)
export interface BridgeSchema {
  // ... existing fields ...

  // Logging configuration (NEW)
  logging?: {
    level: "quiet" | "normal" | "verbose"
    showPathsAbsolute: boolean
    suppressNpmOutput: boolean
    suppressViteBanner: boolean
    timestamps: boolean
  }
}
```

**Flow:**
1. User configures `ViteConfig(logging=LoggingConfig(level="quiet"))` in Python
2. Python writes to `.litestar.json` including `logging` section
3. TypeScript reads `.litestar.json` and applies settings
4. Both Python and TypeScript respect the same config

**Levels:**
- `quiet`: Only errors and essential startup info (single startup line)
- `normal` (default): Current behavior minus duplicates
- `verbose`: Full debug output including all paths, timings, etc.

**Suppressing npm output:**
The `> dev` / `> vite` lines come from npm echoing the script name. To suppress:
```bash
# In package.json scripts, prefix with @:
"dev": "@vite"  # Suppresses echo

# Or use --silent flag when running:
npm run dev --silent
```
We can have the executor add `--silent` when `suppress_npm_output=True`.

## Testing Strategy

### Unit Tests
- Test `formatPath()` helper converts absolute to relative paths correctly
- Test log level filtering respects configuration

### Integration Tests
- Capture startup output and verify no duplicate messages
- Verify all paths in output are relative
- Verify prefix consistency

### Manual Testing
- Start app with `litestar assets serve`, verify clean output
- Start with `--verbose` flag, verify additional debug info
- Start with `--quiet` flag, verify minimal output

## Research Questions

- [x] What logging libraries does Vite use internally? → `resolvedConfig.logger` (Vite's built-in)
- [x] Can we suppress npm script echo (`> dev` / `> vite`)? → No, that's npm's default behavior
- [ ] Should we use structlog for all Python logging instead of Rich console?

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change for users parsing logs | Medium | Keep message content similar, only change format |
| Performance overhead of path calculations | Low | Cache project root, use lazy evaluation |
| Missing important debug info in quiet mode | Medium | Default to "normal" mode, document level behaviors |
| Vite version compatibility | Low | Use `resolvedConfig.logger` which is stable API |

## Implementation Order

1. **Phase 1**: Add `formatPath()` helper to TypeScript, update all path outputs
2. **Phase 2**: Add prefix to Python `_log_*` functions, remove duplicate messages
3. **Phase 3**: Add log level configuration to Python and TypeScript
4. **Phase 4**: Consolidate startup banner (decide on single source of truth)
5. **Phase 5**: Documentation and testing
