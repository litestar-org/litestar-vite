# PRD: Vite Dev Proxy Doctor - Reliable Single-Process Dev, Typegen Defaults, and Config Diagnostics

- **Slug**: vite-dev-proxy-doctor
- **Created**: 2025-11-28
- **Updated**: 2025-11-28
- **Status**: Ready for Implementation

---

## Problem Statement

Running SPA examples via `litestar run` should transparently start a healthy Vite dev server and proxy HMR endpoints (`/@vite/client`, `/@react-refresh`, etc.). Currently, this fails with 404/502 errors because:

1. **Vite child process exits prematurely** - Missing bundled JS plugin files (`install-hint.js`, `litestar-meta.js`) or module resolution failures when using `file:` protocol references
2. **Proxy falls back silently** - When Vite startup fails, the proxy middleware returns unhelpful 502 errors without surfacing the actual failure reason
3. **No diagnostic tooling** - Users have no guided way to diagnose or fix misalignments between Python `ViteConfig` and JavaScript `vite.config.*`
4. **TypeGen not scaffolded by default** - Templates omit Zod/SDK generation configuration, leaving the type generation pipeline unused

---

## Goals

1. **Reliable single-process dev mode** - `litestar run` (with `proxy_mode="proxy"`) reliably starts Vite and proxies HMR endpoints without manual intervention
2. **Actionable error reporting** - Surface Vite child startup failures with actual stderr/stdout, exit codes, and actionable hints
3. **Config doctor command** - Add `litestar assets doctor` to diagnose and auto-fix configuration misalignments between Python and JS configs
4. **TypeGen enabled by default** - Scaffold templates with type generation (Zod + SDK) enabled and properly configured

---

## Non-Goals

- Shipping production CDN/prefetch story
- Reworking Inertia middleware behaviour
- Changing default asset base (`/static/`)
- Supporting Vite versions < 5.0
- Doctor command for non-Vite bundlers

---

## Acceptance Criteria

### Core Functionality
- [ ] `uv run litestar run -p <port>` in `examples/spa-react` starts Vite; `/@vite/client` and `/src/main.tsx` return 200; no 404/502
- [ ] `uv run litestar run` in `examples/inertia` correctly proxies all HMR and source requests
- [ ] `npm run build` in examples passes without local hacks; JS plugin dist includes all required ESM files

### Error Reporting
- [ ] If Vite fails to start, CLI prints: command executed, exit code, first 50 lines of stdout/stderr
- [ ] Error output includes hint: "Run `litestar assets doctor` to diagnose configuration issues"
- [ ] Non-zero exit from Vite child raises `ViteProcessError` with context

### Doctor Command
- [ ] `litestar assets doctor` detects and reports mismatches:
  - `base` vs `assetUrl` mismatch
  - Missing `hotFile` path
  - TypeGen paths not matching between Python and JS
  - Missing `@vite/client` entry when base ≠ `/`
  - JS plugin spread missing or malformed in `vite.config.*`
  - Missing dist files for local `file:` dependency
- [ ] `litestar assets doctor --fix` offers auto-fixes with confirmation prompts
- [ ] `litestar assets doctor --check` exits non-zero if issues found (for CI)
- [ ] Dry-run mode shows proposed changes without applying

### TypeGen Defaults
- [ ] New SPA/Inertia templates include typegen block: `generateZod=True`, `generateSdk=True`
- [ ] Default paths: `output=src/generated`, `openapi_path=src/generated/openapi.json`, `routes_path=src/generated/routes.json`
- [ ] Templates include `vite-env.d.ts` with proper module declarations

---

## Technical Approach

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     litestar run (single port)                    │
├──────────────────────────────────────────────────────────────────┤
│  VitePlugin.server_lifespan()                                    │
│    ├─ ViteProcess.start() ─── spawns ─── npm run dev            │
│    │     └─ On failure: capture stderr/stdout, raise error       │
│    └─ ViteProxyMiddleware ─── proxies ─── /@vite/*, /src/*      │
├──────────────────────────────────────────────────────────────────┤
│  Doctor Command                                                   │
│    ├─ Load ViteConfig (Python)                                   │
│    ├─ Parse vite.config.* (JS via AST or regex)                  │
│    ├─ Compare: base/assetUrl, hotfile, typegen paths             │
│    └─ Report / Auto-fix                                          │
└──────────────────────────────────────────────────────────────────┘
```

### Component Changes

#### 1. ViteProcess Error Surfacing (plugin.py)

Current state: `ViteProcess.start()` captures stdout/stderr only after immediate exit.

Changes needed:
- Enhance error capture to include first 50 lines of output
- Add structured error context to `ViteProcessError`
- Print actionable hint pointing to doctor command
- Ensure stderr/stdout streams are captured in non-blocking manner

```python
# Enhanced ViteProcess.start() pseudo-code
def start(self, command, cwd):
    process = self._executor.run(command, cwd)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        console.print(
            f"[red]Vite process failed[/]\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {process.returncode}\n"
            f"Stderr:\n{stderr[:50_lines]}\n"
            f"[yellow]Hint: Run `litestar assets doctor` to diagnose[/]"
        )
        raise ViteProcessError(...)
```

#### 2. Doctor Command (cli.py)

New command: `litestar assets doctor [--check] [--fix]`

**Checks to implement:**

| Check | Detection | Auto-fix |
|-------|-----------|----------|
| base/assetUrl mismatch | Compare `ViteConfig.asset_url` with JS `assetUrl` | Update JS config |
| hotFile path mismatch | Compare `ViteConfig.hot_file` with JS `hotFile` | Update JS config |
| Missing typegen paths | Check if JS `types.openapiPath` matches Python | Update JS config |
| Missing plugin spread | Parse JS config for `litestar(...)` call | Add spread operator |
| Missing dist files | Check `node_modules/litestar-vite-plugin/dist/*` | Run `npm rebuild` |
| generateZod/SDK mismatch | Compare Python and JS typegen flags | Update JS config |

**Implementation approach:**
- Use regex-based parsing for simple `vite.config.ts` patterns
- Support both `.ts` and `.js` config files
- Backup original before auto-fix
- Interactive confirmation for destructive changes

#### 3. JS Plugin Distribution (index.ts)

Current state: Uses relative imports without extensions; `install-hint.js` and `litestar-meta.js` may be missing from dist.

Changes needed:
- Ensure all relative imports use `.js` extensions for Node16/NodeNext compatibility
- Verify rollup/tsup config includes all source files in dist
- Add explicit exports in `package.json` for subpath imports

```json
// package.json exports field
{
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    },
    "./install-hint": "./dist/install-hint.js",
    "./litestar-meta": "./dist/litestar-meta.js"
  }
}
```

#### 4. Proxy Middleware Enhancements (plugin.py)

Current state: `ViteProxyMiddleware` handles URL decoding and prefix matching.

Changes needed:
- Ensure base-prefixed HMR paths are correctly forwarded
- Add verbose logging mode for debugging proxy issues
- Handle framework-specific prefixes (React, Vue, Svelte, Angular)

**Proxy path prefixes (already defined, verify completeness):**
```python
_PROXY_PATH_PREFIXES = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/node_modules/.vite/",
    "/@analogjs/",  # Angular
    "/src/",
)
```

#### 5. Template Updates

Update templates in `src/py/litestar_vite/templates/` to include:

**vite.config.ts template:**
```typescript
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    ...litestar({
      input: ["{{ resource_dir }}/main.{{ ext }}"],
      assetUrl: "{{ asset_url }}",
      bundleDirectory: "{{ bundle_dir }}",
      resourceDirectory: "{{ resource_dir }}",
      hotFile: "{{ bundle_dir }}/hot",
      types: {
        enabled: true,
        output: "{{ resource_dir }}/generated/types",
        openapiPath: "{{ resource_dir }}/generated/openapi.json",
        routesPath: "{{ resource_dir }}/generated/routes.json",
        generateZod: true,
        generateSdk: true,
      },
    }),
  ],
})
```

**vite-env.d.ts template:**
```typescript
/// <reference types="vite/client" />

declare module "*.css" {
  const content: string
  export default content
}

declare module "*.svg" {
  const content: string
  export default content
}
```

---

## Affected Files

### Python (src/py/litestar_vite/)

| File | Changes |
|------|---------|
| `plugin.py` | Enhanced `ViteProcess.start()` error capture; doctor hint on failure |
| `cli.py` | New `doctor` command with `--check`, `--fix` flags |
| `config.py` | Ensure TypeGenConfig defaults align with JS plugin |
| `exceptions.py` | Add context fields to `ViteProcessError` |

### JavaScript (src/js/)

| File | Changes |
|------|---------|
| `src/index.ts` | Verify `.js` extensions on all imports |
| `src/install-hint.ts` | Ensure included in dist |
| `src/litestar-meta.ts` | Ensure included in dist |
| `package.json` | Add explicit exports map |
| `tsconfig.json` | Verify moduleResolution settings |

### Templates

| File | Changes |
|------|---------|
| `templates/react/vite.config.ts.j2` | Add typegen defaults |
| `templates/vue/vite.config.ts.j2` | Add typegen defaults |
| `templates/svelte/vite.config.ts.j2` | Add typegen defaults |
| `templates/htmx/vite.config.ts.j2` | Add typegen defaults |
| `templates/*/vite-env.d.ts.j2` | Add module declarations |

### Examples

| File | Changes |
|------|---------|
| `examples/spa-react/vite.config.ts` | Update with typegen |
| `examples/spa-vue/vite.config.ts` | Update with typegen |
| `examples/inertia/vite.config.ts` | Update with typegen |

---

## API / CLI Changes

### New Command: `litestar assets doctor`

```
Usage: litestar assets doctor [OPTIONS]

  Diagnose and fix Vite configuration issues.

Options:
  --check         Exit with non-zero status if issues found (for CI)
  --fix           Auto-fix detected issues (with confirmation)
  --no-prompt     Apply fixes without confirmation
  --verbose       Show detailed diagnostic output
  --help          Show this message and exit.
```

**Exit codes:**
- 0: No issues found
- 1: Issues found (when `--check`)
- 2: Auto-fix failed

### TypeGen Config Defaults (Python)

```python
TypeGenConfig(
    enabled=True,  # Changed from False
    output=Path("src/generated"),
    openapi_path=Path("src/generated/openapi.json"),
    routes_path=Path("src/generated/routes.json"),
    generate_zod=True,  # Changed from True (keep)
    generate_sdk=False,  # Keep as opt-in
)
```

---

## Testing Strategy

### Unit Tests

| Test | Coverage |
|------|----------|
| `test_proxy_should_proxy_decoding` | URL decoding for `%40` → `@` |
| `test_proxy_prefix_matching` | All framework-specific prefixes |
| `test_doctor_detect_base_mismatch` | Detects `base` vs `assetUrl` |
| `test_doctor_detect_missing_hotfile` | Detects missing hotFile config |
| `test_doctor_detect_typegen_mismatch` | Detects path misalignments |
| `test_typegen_config_serialization` | Round-trip TypeGenConfig |
| `test_vite_process_error_capture` | Captures stderr on failure |

### Integration Tests

| Test | Coverage |
|------|----------|
| `test_litestar_run_spa_react` | `/@vite/client` returns 200 |
| `test_litestar_run_inertia` | HMR proxy works for Vue |
| `test_doctor_check_mode` | Exit codes in CI mode |
| `test_doctor_fix_mode` | Auto-fix applies changes |

### E2E / Manual Tests

- [ ] `npm run build` in `examples/spa-react` succeeds
- [ ] `npm run build` in `examples/spa-vue` succeeds
- [ ] `npm run build` in `examples/inertia` succeeds
- [ ] `litestar assets doctor --check` on fresh clone returns 0
- [ ] `litestar assets doctor` on misconfigured project reports issues

---

## Research Questions

### Resolved

1. **Should doctor patch HTML (`/@vite/client` vs base)?**
   - No. Rely on Vite plugin middleware to inject `@vite/client`. Doctor should only fix config files.

2. **Bundle vs externalize Vite dependencies?**
   - Externalize heavy deps (lightningcss). Add doctor check for missing optional modules.

### Open

1. **AST vs regex for vite.config parsing?**
   - Recommendation: Start with regex for simple cases; document limitations. AST (e.g., `ts-morph`) can be added later if needed.

2. **Should doctor support `vite.config.mjs` and `vite.config.cjs`?**
   - Recommendation: Support `.ts`, `.js`, `.mts`, `.mjs`. Skip `.cjs` (rare in Vite projects).

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Doctor auto-fix overwrites user customizations | Medium | Medium | Dry-run by default; backup file before fix; require `--fix` flag |
| Regex parsing misses edge cases in vite.config | Medium | High | Document limitations; suggest manual fix for complex configs |
| Bundling dist increases size / misses deps | Medium | Low | Externalize heavy deps; add doctor check for missing modules |
| Base/path rewrites differ per framework | High | Medium | Table-driven prefixes; comprehensive tests across frameworks |
| TypeGen defaults break existing projects | Low | Low | Only apply to new templates; existing configs unchanged |

---

## Dependencies

### Runtime
- Python 3.9+
- Node.js 18+ (for ESM support)
- Vite 5.x, 6.x, or 7.x

### Development
- pytest, pytest-asyncio
- Vitest
- @hey-api/openapi-ts (for typegen)

---

## Success Metrics

1. **Zero 404/502 errors** when running `litestar run` on example projects
2. **< 5 seconds** to Vite dev server ready state
3. **100% detection rate** for common misconfigurations in doctor command
4. **90%+ test coverage** for new code paths

---

## Timeline (Phases, not dates)

1. **Phase 1: Error Surfacing** - Enhance ViteProcess error capture
2. **Phase 2: JS Plugin Fixes** - Ensure dist completeness, extension safety
3. **Phase 3: Doctor Command** - Implement basic checks and reporting
4. **Phase 4: Auto-fix** - Add `--fix` capability with safeguards
5. **Phase 5: Template Updates** - Add typegen defaults to all templates
6. **Phase 6: Testing & Documentation** - Comprehensive test suite, docs update
