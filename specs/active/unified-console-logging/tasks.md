# Tasks: Unified Console Logging

## Phase 0: Quick Fixes (Do First) ✅ COMPLETE

### 0.1 Remove spurious "Vite proxy enabled" message
- [x] Remove `console.print()` from `_configure_vite_proxy()` (plugin.py:1767)
- [x] Remove `console.print()` from `_configure_ssr_proxy()` (plugin.py:1792-1794)
- [x] These messages print during app init for ANY command - wrong timing
- [x] TypeScript already logs proxy status when Vite actually starts

## Phase 1: TypeScript Path Formatting ✅ COMPLETE

### 1.1 Add formatPath helper
- [x] Create `formatPath(absolutePath: string, root?: string): string` in `src/js/src/shared/`
- [x] Handle edge cases (already relative, different drives on Windows, etc.)
- [ ] Add unit tests for path formatting (deferred to Phase 5)

### 1.2 Update index.ts logging
- [x] Update startup banner to use relative paths
- [x] Update type generation logging to use relative paths
- [x] Update schema watching logs to use relative paths and bullet style
- [x] Replace `typesConfig.output` with relative path in "Type Gen" line

### 1.3 Update framework-specific plugins
- [ ] Update `src/js/src/astro.ts` console.log calls to use relative paths (future)
- [ ] Update `src/js/src/nuxt.ts` console.log calls to use relative paths (future)
- [ ] Update `src/js/src/sveltekit.ts` console.log calls to use relative paths (future)

## Phase 2: Python Logging Consistency ✅ COMPLETE

### 2.1 Reduce verbose messages
- [x] Remove "Hotfile written" message (internal detail)
- [x] Remove "Vite proxy target" message (shown in banner)
- [x] Remove "Types unchanged" message (not important)
- [x] Remove "Exporting type metadata for Vite..." message (success message sufficient)

### 2.2 Keep bullet style (user preference)
- [x] User preferred `• ✓` style over `[litestar-vite]` prefix - no changes needed

## Phase 3: Logging Configuration via .litestar.json Bridge ✅ COMPLETE (Core)

### 3.1 Python LoggingConfig ✅
- [x] Add `LoggingConfig` struct to config.py with fields:
  - `level: Literal["quiet", "normal", "verbose"]`
  - `show_paths_absolute: bool = False`
  - `suppress_npm_output: bool = False`
  - `suppress_vite_banner: bool = False`
  - `timestamps: bool = False`
- [x] Add `logging: LoggingConfig | bool | None` field to `ViteConfig`
- [x] Add `logging_config` property for type-safe access

### 3.2 Bridge file integration ✅
- [x] Update `_write_runtime_config_file()` in plugin.py to include logging section
- [x] Update `BridgeSchema` interface in index.ts to include logging
- [x] Read logging config in `loadPythonDefaults()` (automatic via PythonDefaults)

### 3.3 TypeScript logging utility ✅
- [x] Create `createLogger(config: LoggingConfig)` utility in `src/js/src/shared/logger.ts`
- [x] Apply `showPathsAbsolute` setting via `logger.path()` method
- [x] Apply `level` filtering (quiet mode skips startup banner)
- [x] Export `Logger`, `LoggingConfig` types and `createLogger`, `defaultLoggingConfig`

### 3.4 npm output suppression ✅
- [x] Update executor to add `--silent` flag when `suppress_npm_output=True`
- [x] Added `silent` parameter to all executor classes (`JSExecutor`, `CommandExecutor`, `NodeenvExecutor`)
- [x] Added `_apply_silent_flag()` helper to inject `--silent` after `run` in commands
- [x] Supports npm, yarn, pnpm, bun (Deno has empty silent_flag as it doesn't use npm-style flags)
- [x] Pass `suppress_npm_output` from `LoggingConfig` to executor in `_create_executor()`

### 3.5 CLI flags ✅
- [x] Add `--quiet` flag to `vite_serve`, `vite_build`, `vite_install` commands
- [x] Support `LITESTAR_VITE_LOG_LEVEL` environment variable via `_get_default_log_level()`
- [x] Document precedence: CLI (--quiet/--verbose) > env (LITESTAR_VITE_LOG_LEVEL) > config > default
- [x] Added `_apply_cli_log_level()` helper to apply CLI overrides
- [x] Added `reset_executor()` method to `ViteConfig` for resetting executor after config changes

## Phase 4: Startup Banner Consolidation ✅ COMPLETE

### 4.1 Design unified banner
- [x] Simplified banner - removed "Assets Base" and redundant info
- [x] Consolidated to single LITESTAR banner with essential info

### 4.2 Implement in TypeScript
- [x] Updated `configureServer` startup banner (index.ts)
- [x] Removed duplicate information
- [x] Using relative paths in Type Gen output

### 4.3 Update Python startup
- [x] Reduced Python startup logs to essential operational messages
- [x] Vite banner still shows (can be suppressed in future Phase 3)

## Phase 5: Testing and Documentation (FUTURE)

### 5.1 Unit tests
- [ ] Add tests for `formatPath()` helper (TypeScript)
- [ ] Add tests for `_fmt_path()` helper (Python)
- [ ] Add tests for log level filtering

### 5.2 Integration tests
- [ ] Test startup output captures in E2E tests
- [ ] Verify no duplicate messages in captured output
- [ ] Verify relative paths in all output

### 5.3 Documentation
- [ ] Document log level configuration in README
- [ ] Add troubleshooting section for verbose logging
- [ ] Update CHANGELOG with logging improvements

## Quality Gate Checklist

- [x] All tests pass (`make test`)
- [x] Linting clean (`make lint`)
- [ ] 90%+ coverage for new logging utilities (deferred)
- [ ] Manual verification with multiple framework examples
- [x] No regressions in existing functionality
