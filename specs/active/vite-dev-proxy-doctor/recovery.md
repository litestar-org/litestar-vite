# Recovery / Session Resume: Vite Dev Proxy Doctor

**Last Updated**: 2025-11-28
**Status**: Ready for Implementation

---

## Quick Context

**Feature**: Reliable single-process dev proxy + config doctor command + typegen defaults

**Problem Being Solved**: Running SPA examples via `litestar run` fails with 404/502 errors due to Vite child process failures and silent proxy fallbacks. No diagnostic tooling exists to help users align Python and JS configurations.

**Key Deliverables**:
1. Enhanced ViteProcess error surfacing with actionable hints
2. `litestar assets doctor` command for config diagnostics
3. TypeGen defaults enabled in templates
4. JS plugin dist completeness for `file:` protocol usage

---

## Current State

### Phase 1: Planning ✅ COMPLETE
- PRD finalized: `specs/active/vite-dev-proxy-doctor/prd.md`
- Tasks defined: `specs/active/vite-dev-proxy-doctor/tasks.md`
- Research documented: `specs/active/vite-dev-proxy-doctor/research/notes.md`

### Phase 2: Error Surfacing ⏳ NOT STARTED
- Target files: `plugin.py`, `exceptions.py`
- Key changes: Capture stderr/stdout, add doctor hint, enhance exception

### Phase 3: JS Plugin Fixes ⏳ NOT STARTED
- Target files: `src/js/src/index.ts`, `package.json`
- Key changes: Verify imports have `.js` extensions, add exports field

### Phase 4: Doctor Command ⏳ NOT STARTED
- Target files: `cli.py` (new `doctor.py` module)
- Key changes: Config parsing, check implementations, auto-fix

### Phase 5: Template Updates ⏳ NOT STARTED
- Target files: `templates/*/vite.config.ts.j2`, examples
- Key changes: TypeGen defaults, vite-env.d.ts

---

## Files to Revisit

### Python Backend

| File | Purpose | Line References |
|------|---------|-----------------|
| `src/py/litestar_vite/plugin.py` | ViteProcess.start() error capture | Lines 323-360 |
| `src/py/litestar_vite/plugin.py` | ViteProxyMiddleware._should_proxy() | Lines 187-195 |
| `src/py/litestar_vite/plugin.py` | _PROXY_PATH_PREFIXES | Lines 116-127 |
| `src/py/litestar_vite/cli.py` | CLI command group (add doctor) | Lines 37-40 |
| `src/py/litestar_vite/cli.py` | vite_status as reference pattern | Lines 675-710 |
| `src/py/litestar_vite/config.py` | TypeGenConfig defaults | Lines 182-214 |
| `src/py/litestar_vite/exceptions.py` | ViteProcessError enhancement | TBD |

### JavaScript Frontend

| File | Purpose | Line References |
|------|---------|-----------------|
| `src/js/src/index.ts` | Import statements with .js | Lines 12-13 |
| `src/js/src/index.ts` | TypesConfig interface | Lines 26-73 |
| `src/js/src/index.ts` | resolvePluginConfig defaults | Lines 522-544 |
| `src/js/package.json` | Exports field | TBD |

### Templates

| File | Purpose |
|------|---------|
| `src/py/litestar_vite/templates/react/vite.config.ts.j2` | TypeGen defaults |
| `src/py/litestar_vite/templates/vue/vite.config.ts.j2` | TypeGen defaults |
| (similar for svelte, htmx, angular, inertia variants) | TypeGen defaults |

---

## Key Technical Decisions

1. **Python 3.9+ Support**: Use `Optional[T]` and `Union[...]` with stringified type hints. Do NOT use `from __future__ import annotations` or bare `T | None`.

2. **Config Parsing**: Use regex for simple vite.config patterns. Document limitations. AST parsing deferred.

3. **Doctor Auto-fix**: Backup files before modification. Require `--fix` flag. Interactive confirmation by default.

4. **TypeGen Alignment**: JS plugin defaults updated to match Python:
   - `output`: `src/generated/types`
   - `openapiPath`: `src/generated/openapi.json`
   - `routesPath`: `src/generated/routes.json`

5. **Proxy Prefixes**: Current list covers React, Vue, Angular. May need `/@svelte/` and devtools paths.

---

## Suggested Next Steps

### If Starting Fresh
1. Read PRD: `specs/active/vite-dev-proxy-doctor/prd.md`
2. Review tasks: `specs/active/vite-dev-proxy-doctor/tasks.md`
3. Start with Phase 2 (Error Surfacing) - quickest wins

### If Continuing Implementation
1. Check which phase was in progress
2. Review the task checklist for that phase
3. Run `make lint && make test` before making changes
4. Mark tasks complete as you go

### Key Commands
```bash
# Install dependencies
make install

# Run linting
make lint

# Run tests
make test

# Test specific example
cd examples/spa-react && npm run build
cd examples/spa-react && uv run litestar run
```

---

## Blockers & Dependencies

### Current Blockers
- None identified

### External Dependencies
- `@hey-api/openapi-ts` for typegen (npm package)
- Vite 5.x, 6.x, or 7.x

### Internal Dependencies
- ViteProcess changes must be backward compatible
- Doctor command is additive (no breaking changes)

---

## Testing Checklist

Before marking any phase complete:

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] Manual test in relevant example project
- [ ] No regressions in other examples

---

## Contact & Resources

- **PRD**: `specs/active/vite-dev-proxy-doctor/prd.md`
- **Tasks**: `specs/active/vite-dev-proxy-doctor/tasks.md`
- **Research**: `specs/active/vite-dev-proxy-doctor/research/notes.md`
- **Architecture Guide**: `specs/guides/architecture.md`
- **Code Style**: `specs/guides/code-style.md`
