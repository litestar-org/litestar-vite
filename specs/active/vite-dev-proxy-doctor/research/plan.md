# Research Plan: Vite Dev Proxy Doctor

**Status**: ✅ COMPLETE

---

## Research Questions (Answered)

### 1. What minimal bundling/external settings ensure `file:../../` usage works?

**Answer**:
- Externalize heavy optional dependencies (lightningcss, etc.)
- Ensure all relative imports use `.js` extensions for Node16/NodeNext compatibility
- Add explicit `exports` field in package.json
- Add doctor check for missing dist files that suggests `npm rebuild`

### 2. Best-practice proxy prefix set for Vite 6+ across react/vue/svelte/nuxt?

**Answer**: Current prefixes cover most cases:
```python
_PROXY_PATH_PREFIXES = (
    "/@vite", "/@id/", "/@fs/", "/@react-refresh",
    "/@vite/client", "/@vite/env", "/vite-hmr",
    "/node_modules/.vite/", "/@analogjs/", "/src/",
)
```

May need additions:
- `/__vue-devtools__/` - Vue DevTools
- `/@svelte/` - Svelte HMR
- `/__react-devtools__/` - React DevTools

### 3. Feasibility of doctor auto-editing vite.config safely?

**Answer**:
- Regex-based parsing is feasible for common patterns
- Backup file before modification
- Interactive confirmation required by default
- Document limitations for complex configs
- AST parsing (ts-morph) deferred to future enhancement

### 4. How to keep typegen defaults aligned between Python and JS?

**Answer**:
- Python TypeGenConfig defaults are authoritative
- JS plugin defaults updated to match:
  - `output`: `src/generated/types`
  - `openapiPath`: `src/generated/openapi.json`
  - `routesPath`: `src/generated/routes.json`
- Doctor command checks for misalignment

---

## Sources Consulted

1. **Internal Code Analysis**:
   - `src/py/litestar_vite/plugin.py` - ViteProcess, ViteProxyMiddleware
   - `src/py/litestar_vite/config.py` - TypeGenConfig
   - `src/py/litestar_vite/cli.py` - CLI patterns
   - `src/js/src/index.ts` - JS plugin configuration

2. **Project Guides**:
   - `specs/guides/architecture.md`
   - `specs/guides/code-style.md`

3. **External Documentation** (referenced but not fetched):
   - Vite Plugin API: https://vitejs.dev/guide/api-plugin
   - Litestar documentation

---

## Output

Research findings documented in:
- `research/notes.md` - Detailed technical analysis
- `prd.md` - Refined requirements with technical approach
- `tasks.md` - Implementation checklist based on findings
- `recovery.md` - Session resume instructions

---

## Key Findings Summary

1. **HMR endpoints are root-level** regardless of `base` - proxy must handle both
2. **URL decoding works** - `%40` → `@` handled correctly
3. **JS imports have extensions** - verify build output includes all files
4. **TypeGen path mismatch** - Python and JS defaults differ, need alignment
5. **Doctor command feasible** - regex parsing for simple cases
6. **Python 3.9+ support** - use `Optional[T]` with stringified hints
