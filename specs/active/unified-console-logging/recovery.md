# Recovery Guide: Unified Console Logging

## Current State
PRD and task breakdown completed. No implementation has started yet.

## Files Modified
None yet - planning phase complete.

## Files to be Modified

### TypeScript (src/js/src/)
| File | Changes |
|------|---------|
| `shared/format-path.ts` | NEW - Path formatting helper |
| `index.ts` | Update startup banner and type gen logging |
| `astro.ts` | Update console.log calls |
| `nuxt.ts` | Update console.log calls |
| `sveltekit.ts` | Update console.log calls |

### Python (src/py/litestar_vite/)
| File | Changes |
|------|---------|
| `config.py` | Add LogLevel enum and log_level field |
| `plugin.py` | Update _log_* functions, remove duplicates |

## Next Steps

1. **Start with Phase 1.1**: Create the `formatPath()` helper in TypeScript
   - Location: `src/js/src/shared/format-path.ts`
   - Export from `src/js/src/shared/index.ts`
   - Add tests in `src/js/__tests__/format-path.test.ts`

2. **Then Phase 1.2**: Update index.ts logging
   - Focus on lines 628-694 (startup banner)
   - Focus on lines 1540-1600 (type generation)
   - Focus on lines 1650-1660 (watching logs)

3. **Quick win**: Update Python `_log_*` functions (Phase 2.1)
   - Simple string prefix addition
   - No config changes needed

## Context for Resumption

### Key Findings from Analysis

1. **Log Sources Identified**:
   - Python: `_log_success()`, `_log_info()`, `_log_warn()`, `_log_fail()` in plugin.py
   - TypeScript: `resolvedConfig.logger.info()` in index.ts
   - Framework plugins: `console.log()` with `colors.cyan()` prefixes

2. **Duplicate Message Location**:
   - First "Vite proxy enabled": `plugin.py:1773` in `_configure_vite_proxy_middleware`
   - Second appearance: From TypeScript Vite plugin when it loads

3. **Path Formatting**:
   - Python has `_fmt_path()` at line 85 that already tries to use relative paths
   - TypeScript has no equivalent - uses full `process.cwd()` paths

4. **Startup Banner**:
   - TypeScript banner: `index.ts:628-694` in `configureServer` setTimeout callback
   - Shows: Index Mode, Dev Server, App URL, Assets Base, Type Gen
   - Uses `resolvedConfig.logger.info()` for consistent Vite styling

### Design Decisions Made

1. **Prefix Format**: `[litestar-vite]` for all messages (matches existing TS pattern)
2. **Status Icons**: Keep `✓ • ! ✗` from Python, consistent across both
3. **Banner Owner**: TypeScript handles pretty banner, Python handles operational logs
4. **Log Levels**: "quiet", "normal" (default), "verbose"

### Test Commands
```bash
# Run TypeScript tests
npm test -w src/js

# Run Python tests
make test

# Full lint check
make lint

# Manual test - start example app
cd examples/react && litestar assets serve
```

## Rollback Plan

If issues arise during implementation:

1. **TypeScript changes**: Revert to using absolute paths (functionally equivalent)
2. **Python prefix changes**: Remove `[litestar-vite]` prefix from _log_* functions
3. **Duplicate removal**: Re-add the message if any edge case needs it

All changes are additive/cosmetic - no functional behavior changes.
