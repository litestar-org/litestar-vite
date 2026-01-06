---
name: litestar-vite-integration
description: Integrate Litestar backend with Vite frontend in Python/TypeScript projects, including VitePlugin setup, ViteConfig and RuntimeConfig choices, mode/proxy selection, and .litestar.json bridge behavior. Use when wiring litestar-vite, aligning Python and Vite configs, or diagnosing integration issues (HMR, proxying, asset paths).
---

# Litestar Vite Integration

## Overview
Provide a repeatable, minimal integration path and guardrails for Python to Vite configuration.

## Quick Start (minimal integration)

Python (Litestar):

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="spa",
)

app = Litestar(
    plugins=[VitePlugin(config=vite_config)],
)
```

Vite config (TypeScript):

```typescript
import { defineConfig } from 'vite';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    litestarVitePlugin({
      input: ['src/main.ts'],
    }),
  ],
});
```

## Integration Checklist

- Set `ViteConfig.paths.resource_dir` to `src` for non-Inertia templates and `resources` for Inertia templates.
- Treat Python config as the source of truth. The plugin writes `.litestar.json`, and the JS plugin uses it as defaults.
- Keep `vite.config.ts` overrides minimal. Only override when intentionally diverging from Python config.
- Pick `mode` first; then choose `proxy_mode` and dev server strategy.
- Prefer the Litestar CLI for running dev/prod tasks (see the `litestar-assets-cli` skill).

## Mode and Proxy Selection

- `mode="spa"`: Single-page app. Default `proxy_mode="vite"`.
- `mode="template"`: Server-rendered templates with Vite assets.
- `mode="htmx"`: HTMX partials with Vite assets.
- `mode="hybrid"`: Inertia or mixed render paths.
- `mode="framework"` (aliases: `ssr`, `ssg`): Framework SSR/SSG (Nuxt, SvelteKit, Astro).
- `mode="external"`: External dev server managed outside Litestar.

Proxy guidance:

- `proxy_mode="vite"`: Proxy Vite assets only (common for SPA and template modes).
- `proxy_mode="proxy"`: Proxy everything except Litestar routes (framework mode).
- `proxy_mode="direct"`: Expose Vite port directly (two-port setup).
- `proxy_mode=None`: Production, no proxy.

## Config Precedence

Precedence order is:

```
vite.config.ts > .litestar.json > hardcoded defaults
```

Use Python `ViteConfig` for shared values (asset URL, bundle/resource dirs, manifest, hot file). Let Vite read the bridge file.

## Common Misconfigurations

- Vite output paths differ from Python config (bundle_dir, manifest, hot_file).
- Inertia templates using `resources/` but `resource_dir` still set to `src`.
- Overriding `build.outDir` or `server.origin` in `vite.config.ts` without matching Python config.
- Starting Vite with `npm run dev` instead of `litestar assets serve`.

## Troubleshooting Checklist

- Confirm `.litestar.json` exists after app startup.
- Run `litestar assets status` and `litestar assets doctor`.
- Verify `proxy_mode`, `host`, `port`, and `protocol` match the dev server you expect.
- Check `ViteConfig.mode` and ensure it aligns with the frontend framework.

## Related Files

- `src/py/litestar_vite/config/`
- `src/py/litestar_vite/plugin/`
- `src/js/src/index.ts`
- `specs/guides/architecture.md`
- `specs/guides/config-precedence.md`
