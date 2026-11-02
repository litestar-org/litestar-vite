# Production Builds, Granian Native Static & CDN Deployment

Moving a `litestar-vite` application from development to production swaps the live Vite dev proxy for pre-compiled, content-hashed bundles (`manifest.json`), optional Rust-level static serving with Granian (`StaticPlacement.NATIVE`), and one-command cloud storage uploads (`litestar assets deploy`).

--8<-- "tools/docs/includes/diagram-dev-vs-prod.html"

---

## 1. Building Production Bundles (`litestar assets build`)

Run `litestar assets build` during your container or CI build stage:

```bash
litestar assets build
```

This command:

1. Exports `.litestar.json`, `openapi.json`, `routes.json`, and `page-props.json` so TypeScript types are up to date before bundling.
2. Runs `vite build` (and `vite build --ssr` when SSR is enabled) using your configured `RuntimeConfig.executor` (`node`, `bun`, `deno`, `pnpm`, `yarn`).
3. Emits hashed assets (`assets/main-B9x8K2.js`, `assets/main-D4f1A9.css`) and `<bundle_dir>/.vite/manifest.json` (or `manifest.json`).

---

## 2. Production `ViteConfig` & Granian Native Static Serving

In production (`dev_mode=False`), `ViteAssetLoader` reads `manifest.json` once at startup and resolves asset tags with O(1) dictionary lookups.

When paired with [`litestar-granian`](https://github.com/litestar-org/litestar-granian) (`GranianPlugin(static="auto")`), `VitePlugin` exposes a [`StaticServerConfig`](../reference/plugin-and-config.md#litestar_vite.plugin.StaticServerConfig) contract (`StaticPlacement.NATIVE`) so Granian's Rust HTTP worker serves hashed bundle files directly before the request ever enters Python or ASGI:

```python title="docs/examples/learn/production_deploy.py"
--8<-- "docs/examples/learn/production_deploy.py"
```

### How `StaticPlacement.NATIVE` Preserves Security

- **Metadata Blocking**: Internal Vite metadata files (`manifest.json`, `.vite/manifest.json`, `hot`, `.litestar.json`, `ssr-manifest.json`) are blocked from public HTTP access via `_StaticBeforeRequestHook`.
- **Immutable Cache Headers**: Fingerprinted assets under `/static/assets/` receive `Cache-Control: public, max-age=31536000, immutable`.
- **Automatic Fallback (`StaticPlacement.ASGI`)**: If you attach custom ASGI middleware, guards, or custom exception handlers to static routes, `VitePlugin.get_static_server_config()` automatically reports `StaticPlacement.ASGI` with a diagnostic `reason` so Granian delegates back to Litestar's router.

---

## 3. Deploying Bundles to S3, GCS, or Cloudflare R2 (`litestar assets deploy`)

When `DeployConfig` is configured (or `VITE_DEPLOY_STORAGE` is set), `litestar assets deploy` uploads your compiled `bundle_dir` to any [`fsspec`](https://filesystem-spec.readthedocs.io/) storage backend and prunes orphaned files:

```bash
litestar assets deploy --storage s3://my-app-assets-prod/assets --asset-url https://cdn.example.com/assets/
```

Use `--dry-run` in CI pull requests to preview which hashed files would be uploaded or deleted without mutating remote storage:

```bash
litestar assets deploy --dry-run
```
