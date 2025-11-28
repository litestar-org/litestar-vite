# Tasks: Vite Dev Proxy Doctor

## Phase 1: Planning & Research ✓

- [x] Capture problem in PRD
- [x] Analyze existing codebase (plugin.py, cli.py, config.py, index.ts)
- [x] Identify affected components and integration points
- [x] Document proxy path prefixes and framework variations
- [x] Review TypeGenConfig parity between Python and JS

---

## Phase 2: Error Surfacing

### 2.1 ViteProcess Enhancement
- [ ] Add `max_output_lines` parameter to `ViteProcess.start()` (default: 50)
- [ ] Implement non-blocking stderr/stdout capture on process failure
- [ ] Format error output with Rich: command, exit code, truncated output
- [ ] Add doctor hint to error message: "Run `litestar assets doctor` to diagnose"
- [ ] Add context fields to `ViteProcessError` exception class

### 2.2 Exception Enhancement
- [ ] Update `ViteProcessError` in `exceptions.py`:
  - Add `exit_code: int | None` field
  - Add `stderr: str | None` field
  - Add `stdout: str | None` field
  - Add `command: list[str] | None` field

### 2.3 Proxy Verbose Mode
- [ ] Add `VITE_PROXY_DEBUG` environment variable support
- [ ] Log proxy decisions when verbose mode enabled
- [ ] Include upstream response status in debug logs

---

## Phase 3: JS Plugin Distribution

### 3.1 Import Extensions
- [ ] Audit all relative imports in `src/js/src/` for `.js` extensions
- [ ] Verify `index.ts` imports: `./install-hint.js`, `./litestar-meta.js`
- [ ] Verify `nuxt.ts` and `sveltekit.ts` imports

### 3.2 Build Configuration
- [ ] Review `tsconfig.json` for `moduleResolution: "NodeNext"` or `"Node16"`
- [ ] Verify `package.json` has `"type": "module"`
- [ ] Add explicit `exports` field to `package.json`:
  ```json
  "exports": {
    ".": { "import": "./dist/index.js", "types": "./dist/index.d.ts" },
    "./nuxt": { "import": "./dist/nuxt.js", "types": "./dist/nuxt.d.ts" },
    "./sveltekit": { "import": "./dist/sveltekit.js", "types": "./dist/sveltekit.d.ts" }
  }
  ```

### 3.3 Dist Verification
- [ ] Add pre-publish script to verify all expected files in dist
- [ ] Ensure `install-hint.js` and `litestar-meta.js` included in dist
- [ ] Test `file:` protocol installation in example projects

---

## Phase 4: Doctor Command Implementation

### 4.1 Command Structure
- [ ] Create `doctor.py` module in `src/py/litestar_vite/`
- [ ] Add `doctor` command to `cli.py` vite_group
- [ ] Implement CLI options: `--check`, `--fix`, `--no-prompt`, `--verbose`
- [ ] Define exit codes: 0 (ok), 1 (issues found), 2 (fix failed)

### 4.2 Configuration Loading
- [ ] Load `ViteConfig` from app context
- [ ] Implement `find_vite_config()` to locate `vite.config.{ts,js,mts,mjs}`
- [ ] Implement `parse_vite_config()` with regex patterns:
  - Extract `assetUrl` value
  - Extract `bundleDirectory` value
  - Extract `hotFile` value
  - Extract `types` configuration block

### 4.3 Check Implementations
- [ ] `check_asset_url_match()`: Compare Python `asset_url` with JS `assetUrl`
- [ ] `check_hot_file_match()`: Compare Python `hot_file` with JS `hotFile`
- [ ] `check_bundle_dir_match()`: Compare Python `bundle_dir` with JS `bundleDirectory`
- [ ] `check_typegen_paths()`: Compare Python and JS typegen output paths
- [ ] `check_plugin_spread()`: Verify `...litestar(...)` pattern in plugins array
- [ ] `check_dist_files()`: Verify `node_modules/litestar-vite-plugin/dist/*` exists

### 4.4 Issue Reporting
- [ ] Define `DoctorIssue` dataclass with fields: severity, message, fix_hint, auto_fixable
- [ ] Implement `format_issues()` with Rich table output
- [ ] Show diff preview for auto-fixable issues

### 4.5 Auto-fix Implementation
- [ ] Implement `backup_file()` to create `.bak` before modification
- [ ] Implement `fix_asset_url()` with regex replacement
- [ ] Implement `fix_hot_file()` with regex replacement
- [ ] Implement `fix_typegen_paths()` with regex replacement
- [ ] Add confirmation prompt before applying fixes
- [ ] Implement `--no-prompt` for CI/scripted usage

---

## Phase 5: Proxy Middleware Verification

### 5.1 Prefix Coverage
- [ ] Verify `_PROXY_PATH_PREFIXES` includes all Vite 6/7 paths
- [ ] Test Vue devtools path: `/__vue-devtools__/`
- [ ] Test Svelte HMR path: `/@svelte/`
- [ ] Test React devtools path: `/__react-devtools__/`

### 5.2 URL Decoding
- [ ] Verify `%40` → `@` decoding in `_should_proxy()`
- [ ] Add test cases for edge case URL encodings
- [ ] Handle double-encoded paths if needed

### 5.3 Base Prefix Handling
- [ ] Verify paths are correctly prefixed when `base` ≠ `/`
- [ ] Test with `base: '/static/'` configuration
- [ ] Ensure HMR websocket paths include base

---

## Phase 6: Template Updates

### 6.1 Typegen Defaults
- [ ] Update `templates/react/vite.config.ts.j2` with typegen block
- [ ] Update `templates/vue/vite.config.ts.j2` with typegen block
- [ ] Update `templates/vue-inertia/vite.config.ts.j2` with typegen block
- [ ] Update `templates/svelte/vite.config.ts.j2` with typegen block
- [ ] Update `templates/svelte-inertia/vite.config.ts.j2` with typegen block
- [ ] Update `templates/htmx/vite.config.ts.j2` with typegen block
- [ ] Update `templates/angular/vite.config.ts.j2` with typegen block

### 6.2 TypeScript Declarations
- [ ] Create `templates/*/vite-env.d.ts.j2` template
- [ ] Add CSS module declarations
- [ ] Add SVG/image asset declarations
- [ ] Include in scaffolding generator

### 6.3 Example Updates
- [ ] Update `examples/spa-react/vite.config.ts` with typegen
- [ ] Update `examples/spa-vue/vite.config.ts` with typegen
- [ ] Update `examples/spa-svelte/vite.config.ts` with typegen
- [ ] Update `examples/inertia/vite.config.ts` with typegen
- [ ] Update `examples/spa-vue-inertia/vite.config.ts` with typegen
- [ ] Verify all examples build successfully

---

## Phase 7: Testing

### 7.1 Unit Tests
- [ ] `test_vite_process_error_capture`: Verify stderr/stdout capture
- [ ] `test_vite_process_error_context`: Verify exception fields populated
- [ ] `test_proxy_should_proxy_decoding`: URL decode test cases
- [ ] `test_proxy_prefix_matching`: All prefix variations
- [ ] `test_doctor_find_vite_config`: File discovery
- [ ] `test_doctor_parse_vite_config`: Regex extraction
- [ ] `test_doctor_check_asset_url_match`: Mismatch detection
- [ ] `test_doctor_check_typegen_paths`: Path alignment
- [ ] `test_doctor_backup_file`: Backup creation
- [ ] `test_doctor_fix_asset_url`: Regex replacement

### 7.2 Integration Tests
- [ ] `test_litestar_run_spa_react`: Full proxy flow
- [ ] `test_litestar_run_inertia`: Vue HMR proxy
- [ ] `test_doctor_check_exit_codes`: CI mode behavior
- [ ] `test_doctor_fix_applies_changes`: Auto-fix verification

### 7.3 E2E Validation
- [ ] Manual test: `npm run build` in each example
- [ ] Manual test: `litestar run` with proxy mode in spa-react
- [ ] Manual test: `litestar assets doctor --check` on misconfigured project
- [ ] Manual test: `litestar assets doctor --fix` on misconfigured project

---

## Phase 8: Documentation

### 8.1 CLI Documentation
- [ ] Add `litestar assets doctor` to CLI reference
- [ ] Document all flags and exit codes
- [ ] Add troubleshooting examples

### 8.2 Configuration Guide
- [ ] Document typegen configuration alignment
- [ ] Add "Common Issues" section with doctor solutions
- [ ] Include migration guide for existing projects

### 8.3 Architecture Update
- [ ] Update `specs/guides/architecture.md` with doctor command
- [ ] Document proxy middleware internals
- [ ] Add sequence diagram for single-process dev flow

---

## Phase 9: Quality Gate & Handoff

### 9.1 Quality Checks
- [ ] `make lint` passes (zero errors)
- [ ] `make test` passes
- [ ] `make type-check` passes
- [ ] Test coverage ≥ 90% for new code

### 9.2 Anti-pattern Scan
- [ ] No `from __future__ import annotations`
- [ ] Use `Optional[T]` and `Union[...]` with stringified type hints (Python 3.9+ support)
- [ ] No class-based tests (use function-based pytest)
- [ ] No mutable default arguments

### 9.3 Knowledge Capture
- [ ] Update `specs/guides/` if new patterns introduced
- [ ] Document any edge cases discovered
- [ ] Archive workspace to `specs/archive/`

---

## Completion Checklist

- [ ] All acceptance criteria from PRD verified
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Examples working
- [ ] PR ready for review
