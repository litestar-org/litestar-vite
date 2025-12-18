# PRD: Deterministic Builds v2 - Unified Write-on-Change

## Overview
- **Slug**: deterministic-builds-v2
- **Created**: 2025-12-17
- **Status**: Ready for Implementation
- **Predecessor**: PR #162 (partial fix - Python only)

## Problem Statement

PR #162 added deterministic build output and write-on-change logic to the Python side, but:

1. **TypeScript side was completely missed** - `emitPagePropsTypes()` always writes files
2. **Three Python codepaths bypass `write_if_changed`** - direct `write_bytes()` calls
3. **Vite plugin always runs `@hey-api/openapi-ts`** - no input caching
4. **No persistence** - restarts re-run everything

This causes:
- Unnecessary file writes triggering HMR cascades
- Warning spam on every dev server start
- Wasted 1-5s on redundant type generation
- CI "dirty tree" issues

## Goals

1. **Unified architecture**: Python CLI = source of truth, Vite plugin = smart consumer
2. **100% write-on-change coverage**: Every generated file uses change detection
3. **Input caching**: Skip expensive operations when inputs haven't changed
4. **Persistent cache**: Survive dev server restarts
5. **Consistent UX**: All commands show "(updated)" or "(unchanged)"

## Non-Goals

- Changing the fundamental Python/TypeScript split
- Modifying hot file behavior (intentional marker files)
- Adding complex cache invalidation UI

## Acceptance Criteria

- [ ] All Python CLI file writes go through `write_if_changed()`
- [ ] TypeScript `writeIfChanged()` utility uses Buffer.equals() comparison
- [ ] `emitPagePropsTypes()` only writes when content changes
- [ ] `page-props.user.ts` keeps write-once semantics (existsSync check)
- [ ] Vite plugin caches input hashes (openapi.json + config file + options)
- [ ] Cache persists to `node_modules/.cache/litestar-vite/`
- [ ] Cache key includes: input hash + config hash + generator options
- [ ] CLI commands show consistent "(updated)"/"(unchanged)" status
- [ ] Vite logs "(unchanged)" only on buildStart, quiet during watch
- [ ] No regressions in existing tests

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Python CLI (Source of Truth)            │
│  generate-types, export-routes, build, deploy               │
│                                                             │
│  ALL writes → write_if_changed() → "(updated)/(unchanged)"  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Generated JSON Artifacts     │
              │  - openapi.json               │
              │  - routes.json                │
              │  - inertia-pages.json         │
              └───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Vite Plugin (Smart Consumer)               │
│                                                             │
│  1. Check input hash cache                                  │
│  2. Skip @hey-api/openapi-ts if inputs unchanged            │
│  3. writeIfChanged() for page-props.ts                      │
│  4. Persist cache to node_modules/.cache/litestar-vite/     │
└─────────────────────────────────────────────────────────────┘
```

### Affected Files

#### Python (3 bypassed writes to fix)

| File | Line | Current | Fix |
|------|------|---------|-----|
| `cli.py` | 279 | `write_bytes()` | `write_if_changed()` |
| `cli.py` | 295 | `write_text()` | `write_if_changed()` |
| `cli.py` | 1174 | `write_bytes()` | `write_if_changed()` |

#### TypeScript (new utility + modifications)

| File | Change |
|------|--------|
| `src/js/src/shared/write-if-changed.ts` | **NEW** - writeIfChanged utility |
| `src/js/src/shared/typegen-cache.ts` | **NEW** - input hash caching |
| `src/js/src/shared/emit-page-props-types.ts` | Use writeIfChanged at line 324 |
| `src/js/src/shared/typegen-plugin.ts` | Add input caching, skip logic |

### Implementation Details

#### 1. TypeScript writeIfChanged Utility

```typescript
// src/js/src/shared/write-if-changed.ts
import fs from "node:fs"
import path from "node:path"

export interface WriteResult {
  changed: boolean
  path: string
}

/**
 * Write file only if content differs from existing.
 * Uses direct Buffer comparison (more efficient than hashing for small files).
 */
export async function writeIfChanged(
  filePath: string,
  content: string,
  options?: { encoding?: BufferEncoding }
): Promise<WriteResult> {
  const encoding = options?.encoding ?? "utf-8"
  const newBuffer = Buffer.from(content, encoding)

  try {
    const existing = await fs.promises.readFile(filePath)
    if (existing.equals(newBuffer)) {
      return { changed: false, path: filePath }
    }
  } catch {
    // File doesn't exist, will write
  }

  await fs.promises.mkdir(path.dirname(filePath), { recursive: true })
  await fs.promises.writeFile(filePath, newBuffer)
  return { changed: true, path: filePath }
}
```

#### 2. Input Hash Cache

```typescript
// src/js/src/shared/typegen-cache.ts
import fs from "node:fs"
import crypto from "node:crypto"
import path from "node:path"

const CACHE_DIR = "node_modules/.cache/litestar-vite"
const CACHE_FILE = "typegen-cache.json"

interface CacheEntry {
  inputHash: string      // SHA-256 of openapi.json
  configHash: string     // SHA-256 of config file (if exists)
  optionsHash: string    // Hash of generator options
  timestamp: number
}

export async function shouldRunOpenApiTs(
  openapiPath: string,
  configPath: string | null,
  options: { generateSdk: boolean; generateZod: boolean; plugins: string[] }
): Promise<boolean> {
  const cache = await loadCache()
  const inputHash = await hashFile(openapiPath)
  const configHash = configPath ? await hashFile(configPath) : ""
  const optionsHash = hashObject(options)

  const cacheKey = `openapi-ts`
  const entry = cache[cacheKey]

  if (entry &&
      entry.inputHash === inputHash &&
      entry.configHash === configHash &&
      entry.optionsHash === optionsHash) {
    return false // Skip - inputs unchanged
  }

  // Will run - update cache after successful run
  return true
}

export async function updateCache(
  openapiPath: string,
  configPath: string | null,
  options: { generateSdk: boolean; generateZod: boolean; plugins: string[] }
): Promise<void> {
  const cache = await loadCache()
  cache["openapi-ts"] = {
    inputHash: await hashFile(openapiPath),
    configHash: configPath ? await hashFile(configPath) : "",
    optionsHash: hashObject(options),
    timestamp: Date.now()
  }
  await saveCache(cache)
}

async function hashFile(filePath: string): Promise<string> {
  const content = await fs.promises.readFile(filePath)
  return crypto.createHash("sha256").update(content).digest("hex")
}

function hashObject(obj: object): string {
  return crypto.createHash("sha256")
    .update(JSON.stringify(obj, Object.keys(obj).sort()))
    .digest("hex")
}
```

#### 3. Python CLI Fixes

```python
# cli.py line 279 - in _generate_schema_and_routes
# Change from:
types_config.openapi_path.write_bytes(schema_content)
# To:
changed = write_if_changed(types_config.openapi_path, schema_content)
status = "updated" if changed else "unchanged"
console.print(f"[green]✓ Schema exported to {_relative_path(types_config.openapi_path)}[/] [dim]({status})[/]")

# cli.py line 295 - in _generate_schema_and_routes
# Change from:
routes_ts_path.write_text(routes_ts_content, encoding="utf-8")
# To:
changed = write_if_changed(routes_ts_path, routes_ts_content)
status = "updated" if changed else "unchanged"
console.print(f"[green]✓ Typed routes exported to {_relative_path(routes_ts_path)}[/] [dim]({status})[/]")

# cli.py line 1174 - in generate_types
# Change from:
config.types.openapi_path.write_bytes(schema_content)
# To:
changed = write_if_changed(config.types.openapi_path, schema_content)
status = "updated" if changed else "unchanged"
console.print(f"[green]✓ Schema exported to {_relative_path(config.types.openapi_path)}[/] [dim]({status})[/]")
```

## Testing Strategy

### Unit Tests
- `writeIfChanged()` returns correct boolean
- `writeIfChanged()` doesn't write when content matches
- Cache correctly identifies unchanged inputs
- Cache invalidates when config changes
- Cache invalidates when options change

### Integration Tests
- CLI `generate-types` shows "(unchanged)" on second run
- Vite plugin skips `openapi-ts` when inputs unchanged
- `page-props.ts` not rewritten when `inertia-pages.json` unchanged
- Cache survives process restart

### Edge Cases
- Missing cache directory
- Corrupted cache file
- Race conditions during concurrent writes
- Large openapi.json files (streaming hash)

## Consensus Notes

**Gemini 3 Pro (9/10 confidence):**
- Use Buffer.equals() for writes, SHA-256 for cache
- Persist cache to survive restarts
- Protect user stubs (page-props.user.ts)

**GPT 5.2 (8/10 confidence):**
- Cache key MUST include config file + options
- emitPagePropsTypes depends on types.gen.ts - order matters
- Start in-memory, add persistence

**Agreement:**
- Direct content comparison for writes (not hash)
- Hash for cache keys (SHA-256 preferred)
- Must persist cache for restart survival
- Consistent logging across Python/TypeScript

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cache corruption | Medium | Graceful fallback - delete and regenerate |
| Over-caching (stale types) | High | Comprehensive cache key (input + config + options) |
| Race condition on cache write | Low | Atomic write pattern |
| Breaking user customizations | High | Keep write-once for page-props.user.ts |

## Files to Create/Modify

### New Files
- `src/js/src/shared/write-if-changed.ts`
- `src/js/src/shared/typegen-cache.ts`

### Modified Files
- `src/py/litestar_vite/cli.py` (3 locations)
- `src/js/src/shared/emit-page-props-types.ts`
- `src/js/src/shared/typegen-plugin.ts`

## Implementation Order

1. **TypeScript utilities** - writeIfChanged + typegen-cache
2. **emit-page-props-types.ts** - Use writeIfChanged
3. **typegen-plugin.ts** - Add input caching
4. **cli.py** - Fix 3 bypassed writes
5. **Tests** - Unit + integration
6. **Documentation** - Update guides
