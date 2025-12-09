# Configuration Precedence Guide

This guide explains how configuration flows between Python (Litestar) and TypeScript (Vite plugin) in litestar-vite.

## Architecture Overview

**Version**: 0.15.0-beta.2

```
┌─────────────────────┐
│   Python ViteConfig │
│   (VitePlugin)      │
└─────────┬───────────┘
          │ on_app_init()
          ▼
┌─────────────────────┐
│   .litestar.json    │
│   (Bridge File)     │
└─────────┬───────────┘
          │ loadPythonDefaults()
          ▼
┌─────────────────────┐    ┌─────────────────────┐
│   vite.config.ts    │───▶│  Resolved Config    │
│   (User TS Config)  │    │  + Validation       │
└─────────────────────┘    └─────────────────────┘
```

## Precedence Chain

**`vite.config.ts` > `.litestar.json` > hardcoded defaults**

1. **vite.config.ts** - Explicit user configuration takes highest priority
2. **.litestar.json** - Python-generated bridge file provides defaults
3. **Hardcoded defaults** - Built-in fallbacks when neither is available

## The Bridge File (`.litestar.json`)

When Litestar starts, it writes a `.litestar.json` file containing shared configuration:

```json
{
  "assetUrl": "/static/",
  "bundleDir": "public/static",
  "resourceDir": "resources",
  "publicDir": "public",
  "hotFile": "hot",
  "manifest": "manifest.json",
  "mode": "spa",
  "proxyMode": "vite_proxy",
  "port": 5173,
  "host": "127.0.0.1",
  "ssrEnabled": false,
  "ssrOutDir": null,
  "types": {
    "enabled": true,
    "output": "src/generated",
    "openapiPath": "src/generated/openapi.json",
    "routesPath": "src/generated/routes.json",
    "generateZod": true,
    "generateSdk": true,
    "globalRoute": false
  },
  "executor": "node",
  "logging": {
    "level": "normal",
    "showPathsAbsolute": false,
    "suppressNpmOutput": false,
    "suppressViteBanner": false,
    "timestamps": false
  },
  "litestarVersion": "2.15.0"
}
```

## Field Classification

### Shared Fields (in `.litestar.json`)

These fields are meaningful to both Python and TypeScript:

| Field | Python Name | JSON/TypeScript Name | Description |
|-------|-------------|---------------------|-------------|
| Asset URL | `asset_url` | `assetUrl` | Base URL for assets |
| Bundle Directory | `bundle_dir` | `bundleDir` | Build output directory |
| Resource Directory | `resource_dir` | `resourceDir` | Source assets directory |
| Public Directory | `public_dir` | `publicDir` | Static assets directory |
| Hot File | `hot_file` | `hotFile` | Dev server URL file |
| Manifest Name | `manifest_name` | `manifest` | Build manifest filename |
| Mode | `mode` | `mode` | Operation mode |
| Proxy Mode | `proxy_mode` | `proxyMode` | Dev proxy configuration |
| Host | `host` | `host` | Dev server host |
| Port | `port` | `port` | Dev server port |
| SSR Enabled | `ssr_enabled` | `ssrEnabled` | SSR mode flag |
| SSR Output Dir | `ssr_output_dir` | `ssrOutDir` | SSR build output |
| Executor | `runtime.executor` | `executor` | Package manager command |
| Logging | `logging` | `logging` | Logging configuration |

### Python-Only Fields

These are configured in Python and not exposed to TypeScript:

- `DeployConfig` - CDN deployment settings (storage_backend, delete_orphaned, include_manifest, content_types)
- `SPAConfig` - Single-page app settings (inject_csrf, cache_transformed_html, csrf_var_name, app_selector)
- `InertiaConfig` - Inertia.js integration settings (root_template, component_opt_keys, spa_mode, encrypt_history, type_gen)
- `InertiaTypeGenConfig` - Inertia type generation (include_default_auth, include_default_flash)
- `RuntimeConfig.run_command`, `build_command`, `serve_command`, `install_command`, etc.
- `RuntimeConfig.http2`, `start_dev_server`, `health_check`, `detect_nodeenv`, `set_environment`, `set_static_folders`, `csp_nonce`, `spa_handler`
- `ExternalDevServer` - External dev server config (target, command, build_command, http2, enabled)
- `PaginationContainer` - Protocol for pagination unwrapping

### TypeScript-Only Fields

These are configured in `vite.config.ts` only:

- `input` - Entry point files
- `refresh` - HMR file patterns
- `detectTls` - Auto-detect HTTPS
- `autoDetectIndex` - Find index.html
- `transformOnServe` - HTML transforms in dev
- `types.debounce` - File watch debounce
- Vite-specific plugins, aliases, etc.

## Naming Convention

- **JSON/TypeScript**: `camelCase` (JavaScript convention)
- **Python**: `snake_case` (Python convention)

The bridge file uses camelCase since it's primarily consumed by JavaScript.

## Configuration Validation

The TypeScript plugin validates configuration against Python defaults and warns on mismatches:

```
[litestar-vite] Configuration mismatch detected:
  • bundleDir: vite.config.ts="dist" differs from Python="public"

Precedence: vite.config.ts > .litestar.json > defaults
See: https://docs.litestar.dev/vite/config-precedence
```

This helps catch configuration drift between Python and TypeScript.

## Best Practices

### 1. Let Python Drive Shared Config

Configure shared settings in Python's `ViteConfig`:

```python
# app.py
vite = VitePlugin(
    config=ViteConfig(
        paths=PathConfig(
            bundle_dir=Path("public/static"),
            resource_dir=Path("resources"),
        ),
        asset_url="/static/",
    )
)
```

### 2. Keep vite.config.ts Minimal

Only specify TypeScript-specific options:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    litestar({
      input: ["src/main.ts"],  // Required: entry points
      // Let Python defaults handle the rest
    }),
  ],
})
```

### 3. Override Only When Necessary

If you need to override Python defaults in TypeScript:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    litestar({
      input: ["src/main.ts"],
      bundleDir: "dist",  // Override Python default
      // Warning will be shown if this differs from .litestar.json
    }),
  ],
})
```

### 4. Run Litestar First in Development

The bridge file is created when Litestar starts:

```bash
# Start Litestar (creates .litestar.json)
litestar run

# Or use the integrated command
litestar assets serve
```

## Standalone JavaScript Mode

For projects not using Litestar's Python backend, configure everything in TypeScript:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    litestar({
      input: ["src/main.ts"],
      assetUrl: "/static/",
      bundleDir: "dist",
      resourceDir: "src",
      types: false,  // Disable type generation without Python
    }),
  ],
})
```

## Troubleshooting

### Missing .litestar.json Warning

If you see a warning about missing `.litestar.json`:

1. Start the Litestar backend first: `litestar run`
2. Or configure all options explicitly in `vite.config.ts`

### Configuration Mismatch Warning

If you see configuration mismatch warnings:

1. Review your `vite.config.ts` overrides
2. Either remove the override to use Python defaults
3. Or update Python config to match your TypeScript settings

### Debugging Configuration

Run the doctor command to diagnose issues:

```bash
litestar assets doctor
```

This shows a side-by-side comparison of Python and TypeScript configuration.
