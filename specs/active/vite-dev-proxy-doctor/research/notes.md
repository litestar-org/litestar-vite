# Research Notes: Vite Dev Proxy Doctor

**Date**: 2025-11-28
**Updated**: 2025-11-28

---

## Executive Summary

The single-process dev mode (`litestar run` with `proxy_mode="proxy"`) requires reliable Vite child process management and transparent HMR proxying. Current implementation has gaps in error surfacing, JS plugin distribution, and configuration diagnostics. This document captures findings from codebase analysis to inform implementation.

---

## 1. Vite Dev Proxy Behaviour

### 1.1 HMR Endpoint Routing

HMR endpoints are always rooted at `/@vite/*` regardless of `base` configuration:

- When `base` is `/static/`, the dev server still serves `/@vite/client` at the root
- Asset URLs in generated code include the base prefix
- Source file requests use URL path as-is (e.g., `/src/main.tsx`)

**Key insight**: Proxy must handle both root-level HMR paths AND base-prefixed asset paths.

### 1.2 Current Proxy Path Prefixes

From `plugin.py:116-127`:
```python
_PROXY_PATH_PREFIXES: tuple[str, ...] = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/node_modules/.vite/",
    "/@analogjs/",
    "/src/",
)
```

**Missing prefixes to investigate**:
- `/__vue-devtools__/` - Vue devtools integration
- `/@svelte/` - Svelte HMR specific
- `/__react-devtools__/` - React devtools

### 1.3 URL Decoding

The proxy correctly handles URL-encoded paths (e.g., `/%40vite/client` → `/@vite/client`):

```python
# From plugin.py:187-195
def _should_proxy(self, path: str) -> bool:
    from urllib.parse import unquote
    decoded = unquote(path)
    return decoded.startswith(self._proxy_path_prefixes) or path.startswith(self._proxy_path_prefixes)
```

### 1.4 Vite Child Process Failure

When Vite child dies on startup (missing deps), the proxy falls back and returns 404/502. Current error handling in `ViteProcess.start()` (lines 323-360) captures output but could be improved:

- Output capture happens only on immediate exit
- Doctor hint not yet implemented
- Exception context fields not structured

---

## 2. JS Plugin Distribution

### 2.1 Import Statement Analysis

From `src/js/src/index.ts`:
```typescript
import { resolveInstallHint } from "./install-hint.js"
import { type LitestarMeta, loadLitestarMeta } from "./litestar-meta.js"
```

**Status**: Extensions are present. Verify build output includes these files.

### 2.2 Current Build Issues

Using `file:../../` in example `package.json` requires:
1. Built ESM files present with explicit `.js` imports
2. All referenced modules included in dist
3. Node16/NodeNext resolution compatibility

**Known missing files** (from user reports):
- `install-hint.js` - occasionally missing from dist
- `litestar-meta.js` - occasionally missing from dist

### 2.3 Package.json Exports

Current `src/js/package.json` should be verified for:
```json
{
  "type": "module",
  "exports": {
    ".": { "import": "./dist/index.js", "types": "./dist/index.d.ts" },
    "./nuxt": { "import": "./dist/nuxt.js", "types": "./dist/nuxt.d.ts" },
    "./sveltekit": { "import": "./dist/sveltekit.js", "types": "./dist/sveltekit.d.ts" }
  }
}
```

---

## 3. TypeGen Configuration Analysis

### 3.1 Python TypeGenConfig (config.py:182-214)

```python
@dataclass
class TypeGenConfig:
    enabled: bool = False
    output: Path = field(default_factory=lambda: Path("src/generated"))
    openapi_path: Path = field(default_factory=lambda: Path("src/generated/openapi.json"))
    routes_path: Path = field(default_factory=lambda: Path("src/generated/routes.json"))
    generate_zod: bool = True
    generate_sdk: bool = False
    watch_patterns: list[str] = field(
        default_factory=lambda: ["**/routes.py", "**/handlers.py", "**/controllers/**/*.py"]
    )
```

### 3.2 JS TypesConfig (index.ts:26-73)

```typescript
export interface TypesConfig {
  enabled?: boolean          // default: false (but resolves to true if types present)
  output?: string            // default: 'src/types/api' → MISMATCH
  openapiPath?: string       // default: 'openapi.json' → MISMATCH
  routesPath?: string        // default: 'routes.json' → MISMATCH
  generateZod?: boolean      // default: false
  generateSdk?: boolean      // default: false
  debounce?: number          // default: 300
}
```

### 3.3 Default Path Mismatches

| Setting | Python Default | JS Default | Aligned Default |
|---------|---------------|------------|-----------------|
| `output` | `src/generated` | `src/types/api` | `src/generated` |
| `openapiPath` | `src/generated/openapi.json` | `openapi.json` | `src/generated/openapi.json` |
| `routesPath` | `src/generated/routes.json` | `routes.json` | `src/generated/routes.json` |
| `enabled` | `False` | `true` (implicit) | `True` |
| `generateZod` | `True` | `false` | `True` |

**Action**: Update JS defaults to match Python, or document the alignment requirement.

### 3.4 Resolution in JS Plugin (index.ts:522-544)

```typescript
// Resolve types configuration (default enabled)
let typesConfig: Required<TypesConfig> | false = false
if (resolvedConfig.types === true || typeof resolvedConfig.types === "undefined") {
  typesConfig = {
    enabled: true,
    output: "src/generated/types",
    openapiPath: "src/generated/openapi.json",
    routesPath: "src/generated/routes.json",
    generateZod: false,
    generateSdk: false,
    debounce: 300,
  }
}
```

**Observation**: JS plugin defaults to enabled with sensible paths when `types` is undefined or `true`.

---

## 4. Doctor Command Design

### 4.1 Vite Config File Locations

Search order for vite.config:
1. `vite.config.ts`
2. `vite.config.js`
3. `vite.config.mts`
4. `vite.config.mjs`

### 4.2 Regex Patterns for Config Parsing

**Extract assetUrl**:
```regex
assetUrl\s*:\s*["']([^"']+)["']
```

**Extract bundleDirectory**:
```regex
bundleDirectory\s*:\s*["']([^"']+)["']
```

**Extract hotFile**:
```regex
hotFile\s*:\s*["']([^"']+)["']
```

**Detect plugin spread**:
```regex
\.\.\.\s*litestar\s*\(
```

### 4.3 Check Priority

1. **Critical**: Plugin spread missing → Vite won't work at all
2. **High**: base/assetUrl mismatch → Assets 404
3. **High**: Missing dist files → Module resolution failure
4. **Medium**: TypeGen path mismatch → Types not generated correctly
5. **Low**: HotFile path mismatch → HMR may not detect server

---

## 5. Existing CLI Commands Analysis

### 5.1 Current `vite_group` Commands (cli.py)

| Command | Purpose |
|---------|---------|
| `init` | Initialize Vite project with templates |
| `install` | Install frontend packages |
| `build` | Build frontend assets |
| `serve` | Start Vite dev server |
| `export-routes` | Export route metadata |
| `generate-types` | Generate TypeScript types |
| `status` | Check Vite integration status |

### 5.2 Status Command as Reference

`vite_status` (cli.py:675-710) provides a pattern for doctor:
- Loads plugin config from app context
- Checks manifest file existence
- Tests dev server connectivity
- Uses Rich for formatted output

---

## 6. Error Handling Patterns

### 6.1 Current ViteProcessError

From `exceptions.py` (to be verified):
```python
class ViteProcessError(Exception):
    """Raised when the Vite process fails."""
    pass
```

### 6.2 Enhanced Exception Design

**Note**: Project supports Python 3.9+, so use `Optional[T]` and `Union[...]` with stringified type hints (no `from __future__ import annotations`).

```python
from typing import Optional

@dataclass
class ViteProcessError(Exception):
    message: str
    exit_code: "Optional[int]" = None
    stderr: "Optional[str]" = None
    stdout: "Optional[str]" = None
    command: "Optional[list[str]]" = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.exit_code is not None:
            parts.append(f"Exit code: {self.exit_code}")
        if self.stderr:
            parts.append(f"Stderr:\n{self.stderr}")
        return "\n".join(parts)
```

---

## 7. Open Questions (Resolved)

### 7.1 Should doctor auto-rewrite HTML?

**Decision**: No. The Vite plugin middleware injects `@vite/client` automatically. Doctor should only fix configuration files, not HTML templates.

### 7.2 Should JS dist be bundled to include optional deps?

**Decision**: Externalize heavy dependencies (lightningcss, etc.). Add a doctor check for missing modules that suggests `npm rebuild`.

### 7.3 AST vs regex for vite.config parsing?

**Decision**: Start with regex for common patterns. Document limitations. AST parsing (ts-morph) can be added as enhancement if regex proves insufficient.

---

## 8. Framework-Specific Considerations

### 8.1 React
- `/@react-refresh` - Fast Refresh HMR
- `/__react-devtools__/` - DevTools integration

### 8.2 Vue
- Standard `/@vite/*` paths
- `/__vue-devtools__/` - Vue DevTools

### 8.3 Svelte
- `/@svelte/` - Svelte HMR specific
- Standard HMR otherwise

### 8.4 Angular
- `/@analogjs/` - Analog framework paths
- May need additional prefixes for Angular 18+

### 8.5 Inertia
- Same as underlying framework (Vue, React, Svelte)
- No additional HMR paths

---

## 9. Implementation Recommendations

### 9.1 Phase Ordering

1. **Error surfacing first** - Quick wins, immediate debugging value
2. **JS plugin dist second** - Enables reliable Vite startup
3. **Doctor command third** - Comprehensive diagnostics
4. **Template updates last** - Lower priority, affects new projects only

### 9.2 Test Strategy

- Mock subprocess for ViteProcess tests
- Use temp directories for doctor config parsing tests
- Integration tests should use actual example projects

### 9.3 Backward Compatibility

- TypeGen default changes only affect new ViteConfig instances
- Existing projects with explicit config unaffected
- Doctor command is additive (no breaking changes)

---

## 10. References

- Vite Plugin API: https://vitejs.dev/guide/api-plugin
- Litestar CLI: `src/py/litestar_vite/cli.py`
- Proxy Middleware: `src/py/litestar_vite/plugin.py:151-278`
- JS Plugin: `src/js/src/index.ts`
