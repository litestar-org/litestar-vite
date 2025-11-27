# Recovery: Litestar-Vite v2.0 Unified Redesign

**Last Updated**: 2025-11-27
**Status**: PRD Complete, Ready for Implementation

---

## Quick Context

This is a **complete v2.0 redesign** that unifies three initiatives:

1. **v2.0 Architecture Redesign** - Async-first, DI, clean config (from `litestar-vite-v2-redesign`)
2. **Type-Safe Routing** - Auto-generated TypeScript + Zod (from `type-safe-routing`)
3. **Template System Cleanup** - Remove forced Jinja, support SPA mode (from `remove-custom-template-config` branch)

**Key Principle**: Simple but powerful. Zero-config for common cases, full customization when needed.

---

## What's Being Built

### Dual Mode System

| Mode | Use Case | Template Required? |
|------|----------|-------------------|
| **SPA** | React, Vue, Svelte, Inertia | No - standard `index.html` |
| **Template** | Server-rendered, hybrid | Yes - Jinja templates |
| **HTMX** | Hypermedia apps | Yes - with HTMX helpers |

### Type Generation Pipeline

```
Python Routes → OpenAPI Schema → @hey-api/openapi-ts → TypeScript + Zod
                     ↓
              Routes Metadata → Typed route() helper
```

### Configuration (Simple)

```python
# Zero-config SPA
VitePlugin()

# With type generation
VitePlugin(config=ViteConfig(types=True))

# Full Inertia setup
VitePlugin(config=ViteConfig(types=True, inertia=True))

# Template mode
VitePlugin(config=ViteConfig(mode="template"))
```

---

## Files Created

| File | Purpose |
|------|---------|
| `specs/active/litestar-vite-v2-unified/prd.md` | Unified PRD |
| `specs/active/litestar-vite-v2-unified/tasks.md` | Implementation tasks |
| `specs/active/litestar-vite-v2-unified/recovery.md` | This file |

## Files to Supersede

These older workspaces are now merged into this unified plan:

- `specs/active/litestar-vite-v2-redesign/` - Architecture redesign
- `specs/active/type-safe-routing/` - Type-safe routing

---

## Key Decisions

| Decision | Resolution |
|----------|------------|
| **Breaking changes?** | Yes - clean slate for v2.0 |
| **SPA mode default?** | Yes - most common use case |
| **Jinja required?** | No - optional, only for template mode |
| **Type generator?** | `@hey-api/openapi-ts` (Zod support) |
| **Singleton loader?** | No - proper DI |
| **Sync I/O?** | No - async-first with anyio |
| **Dev server approach?** | **Vite Sidecar** - single port, zero config |
| **HMR WebSocket?** | Proxied through Python - uses `server.hmr.clientPort` |

---

## Implementation Order

1. **Phase 1: Core Architecture** - Config, async loader, DI, plugin
2. **Phase 2: Dual Mode** - SPA handler, HTML injection, template mode
3. **Phase 3: Type Generation** - CLI, codegen, Vite plugin integration
4. **Phase 4: Inertia** - Enhanced injection, page props typing
5. **Phase 5: Polish** - Examples, docs, tests

---

## Key Files to Modify

### Python

| File | Changes |
|------|---------|
| `src/py/litestar_vite/config.py` | Complete rewrite - nested configs |
| `src/py/litestar_vite/loader.py` | Async rewrite, remove singleton |
| `src/py/litestar_vite/plugin.py` | DI registration, mode handling |
| `src/py/litestar_vite/executor.py` | NEW - ViteExecutor (sidecar subprocess management) |
| `src/py/litestar_vite/spa.py` | NEW - SPA handler |
| `src/py/litestar_vite/html.py` | NEW - HTML transformer |
| `src/py/litestar_vite/codegen.py` | NEW - Route metadata extraction |
| `src/py/litestar_vite/cli.py` | New commands including `vite init` |
| `src/py/litestar_vite/scaffolding/` | NEW - Project scaffolding module |
| `src/py/litestar_vite/scaffolding/ui.py` | NEW - Rich-based interactive UI |
| `src/py/litestar_vite/scaffolding/generator.py` | NEW - Template generation |
| `src/py/litestar_vite/template_engine.py` | DELETE |

### Templates

| Directory | Contents |
|-----------|----------|
| `templates/base/` | Shared templates (vite.config.ts.j2, package.json.j2, etc.) |
| `templates/react/` | React SPA templates |
| `templates/vue/` | Vue 3 SPA templates |
| `templates/vue-inertia/` | Vue + Inertia.js templates |
| `templates/svelte/` | Svelte 5 SPA templates |
| `templates/sveltekit/` | SvelteKit templates |
| `templates/htmx/` | HTMX + Alpine.js templates |
| `templates/astro/` | Astro templates |
| `templates/addons/tailwindcss/` | TailwindCSS addon templates |

### TypeScript

| File | Changes |
|------|---------|
| `src/js/src/index.ts` | Add `types` config option |
| `src/js/src/sidecar.ts` | NEW - Vite sidecar bootstrap script |
| `src/js/src/codegen/` | NEW - Route helper generator |

---

## To Resume Work

```bash
# Read the unified PRD
cat specs/active/litestar-vite-v2-unified/prd.md

# Read the tasks
cat specs/active/litestar-vite-v2-unified/tasks.md

# Check current implementations
cat src/py/litestar_vite/config.py
cat src/py/litestar_vite/loader.py
cat src/py/litestar_vite/plugin.py

# Check old branch for reference
git show remove-custom-template-config:src/py/litestar_vite/config.py
```

---

## Vite Sidecar Architecture (Zero-Config Dev Server)

The v2.0 redesign introduces a **Vite Sidecar** architecture for truly seamless development:

```
Browser (port 8000 only)
    │
    ▼
Litestar (Python)
    ├─► /api/* → Litestar handlers
    ├─► /@vite/* → Proxy to internal Vite
    ├─► /__vite_hmr__ (WS) → WebSocket proxy
    └─► /* → HTML from Vite
              │
              ▼ (internal ephemeral port)
         Vite Sidecar (Node.js subprocess)
```

**Key Components:**
- `ViteExecutor` - Manages Node.js subprocess lifecycle
- `sidecar.ts` - Bootstrap script running Vite in `middlewareMode`
- WebSocket proxy - Forwards HMR messages bidirectionally

**Critical Vite Config:**
```typescript
server: {
  middlewareMode: true,
  hmr: {
    clientPort: 8000,  // Browser connects to Python's port
    path: '/__vite_hmr__',
  },
}
```

**Auto-Detection:**
1. Production manifest exists → production mode
2. Vite running on 5173 → use external Vite
3. `vite.config.ts` exists → start sidecar
4. Nothing detected → production mode

---

## Keeping Templates & Docs Updated

Before implementing or releasing, run these update procedures:

### Quick Update Commands

```bash
# Check Vite backend integration docs
# Use Context7 MCP:
# mcp__context7__get-library-docs(context7CompatibleLibraryID="/websites/vite_dev", topic="backend integration")

# Or fetch directly:
curl -s https://raw.githubusercontent.com/vitejs/vite/main/docs/guide/backend-integration.md | head -200

# Check @hey-api/openapi-ts version
npm view @hey-api/openapi-ts version

# Check litestar-htmx for new features
gh api repos/litestar-org/litestar-htmx/releases/latest --jq '.tag_name'

# Check Inertia.js protocol
curl -s https://inertiajs.com/the-protocol | head -100
```

### Key Files to Verify Against Upstream

| Our File | Upstream Source | What to Check |
|----------|-----------------|---------------|
| `loader.py` | Vite manifest docs | `ManifestChunk` fields |
| `loader.py` | Vite HMR docs | `@vite/client` path |
| `inertia/response.py` | Inertia protocol | Headers, page object |
| `src/js/index.ts` | Vite plugin API | Hook signatures |
| Examples | All deps | Working with latest versions |

### PR #32 Reference

PR #32 had useful template patterns. Key files:

- `examples/basic/vite.config.ts` - Standard Vite config with litestar plugin
- `examples/basic/templates/index.html.j2` - Jinja template with `{{ vite() }}`
- `litestar_vite/templates/vite.config.ts.j2` - Scaffold template

---

## Reference Materials

### Branches

- `remove-custom-template-config` - Template cleanup work
- `remotes/cj/cj-patch-allow-no-template-config` - Optional template config

### External Docs (Check These!)

| Resource | URL | What We Use |
|----------|-----|-------------|
| Vite Backend Integration | https://vite.dev/guide/backend-integration | Manifest format, dev injection |
| Litestar Plugins | https://docs.litestar.dev/latest/usage/plugins/ | InitPlugin API |
| Litestar HTMX | https://docs.litestar.dev/latest/usage/htmx | **Don't duplicate this!** |
| @hey-api/openapi-ts | https://heyapi.dev/ | Type generation |
| Inertia Protocol | https://inertiajs.com/the-protocol | Headers, response format |

### GitHub Resources

- [@hey-api/openapi-ts](https://github.com/hey-api/openapi-ts)
- [Ziggy](https://github.com/tighten/ziggy) - Route helper inspiration
- [litestar-htmx](https://github.com/litestar-org/litestar-htmx) - Use, don't duplicate
- [PR #32](https://github.com/litestar-org/litestar-vite/pull/32) - CLI template reference
