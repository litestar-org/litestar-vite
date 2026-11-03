# Production Builds, Granian Native Static & CDN Deployment

Moving a Litestar Vite application from development to production swaps the live Vite dev proxy for pre-compiled, content-hashed bundles (`manifest.json`), optional Rust-level static serving with Granian (`StaticPlacement.NATIVE`), and one-command cloud storage uploads (`litestar assets deploy`).

--8<-- "tools/docs/includes/diagram-dev-vs-prod.html"

---

## Building Production Bundles

Run `litestar assets build` during your container or CI build stage:

<!-- termynal -->

```console
$ litestar assets build
✓ Exported .litestar.json, openapi.json, and routes.json
✓ Running vite build...
---> 100%
public/.vite/manifest.json                0.42 kB
public/assets/main-D4f1A9.css            12.84 kB │ gzip:  3.12 kB
public/assets/main-B9x8K2.js            148.20 kB │ gzip: 46.50 kB
✓ Built in 1.42s
```

This command:

1. Exports `.litestar.json`, `openapi.json`, `routes.json`, and `inertia-pages.json` so TypeScript types are up to date before bundling.
2. Runs `vite build` (and `vite build --ssr` when SSR is enabled) using your configured `RuntimeConfig.executor` (`node`, `bun`, `deno`, `pnpm`, `yarn`).
3. Emits hashed assets (`assets/main-B9x8K2.js`, `assets/main-D4f1A9.css`) and `<bundle_dir>/.vite/manifest.json` (or `manifest.json`).

---

## Production Configuration & Granian Static Serving

In production (`dev_mode=False`), `ViteAssetLoader` reads `manifest.json` once at startup and resolves asset tags with O(1) dictionary lookups.

When paired with [`litestar-granian`](https://github.com/litestar-org/litestar-granian) (`GranianPlugin(static="auto")`), `VitePlugin` exposes a [`StaticServerConfig`](../reference/runtime-and-assets.md#litestar_vite.plugin.StaticServerConfig) contract (`StaticPlacement.NATIVE`) so Granian's Rust HTTP worker serves hashed bundle files directly before the request ever enters Python or ASGI:

```python title="docs/examples/learn/production_deploy.py"
--8<-- "docs/examples/learn/production_deploy.py"
```

### Server & Static Placement Matrix

| ASGI Server | Static Serving Mechanism | Metadata Blocking (`manifest.json`, `hot`) | Immutable Cache Headers |
| --- | --- | --- | --- |
| **Granian (`StaticPlacement.NATIVE`)** | Rust HTTP worker serves static files before Python/ASGI | Router hooks preserve `StaticPlacement.NATIVE`; configure equivalent server/CDN rules for native hits | Configure at server/CDN layer for native hits |
| **Uvicorn / Hypercorn (`StaticPlacement.ASGI`)** | Litestar `create_static_files_router` | Enforced via `_StaticBeforeRequestHook` (404 Not Found) | Enforced via `_StaticAfterRequestHook` |

---

## Asset Headers, Preloading, SRI, and CSP

Production HTML and asset responses served by Litestar apply browser-facing performance and security optimizations controlled by [`RuntimeConfig`](../reference/plugin-and-config.md#litestar_vite.config.RuntimeConfig) and [`ViteAssetLoader`](../reference/runtime-and-assets.md#litestar_vite.loader.ViteAssetLoader):

| Setting | Behavior |
| --- | --- |
| `immutable_cache_headers=True` | Files under the Vite `assets` directory whose names carry a Rollup content hash (`index-D8x9kL2p.js`) receive `Cache-Control: public, max-age=31536000, immutable`. Unhashed files (`favicon.ico`, `icon-192x192.png`) are untouched. |
| `link_preload_headers=True` | HTML responses include an RFC 8288 `Link` header with `rel=modulepreload` for the served entry and its transitive chunks and `rel=preload; as=style` for their stylesheets. Computed once per process from `manifest.json`. |
| `early_hints=True` (opt-in) | Sends the same preload links as a `103 Early Hints` frame when the ASGI server advertises `http.response.early_hint` in `scope["extensions"]` (for example Hypercorn). Servers without the extension receive only the `Link` header. |
| `csp_nonce="..."` | Inline and entry scripts carry `nonce="..."`. Inertia and template responses also honor a per-request `request.scope["state"]["csp_nonce"]` set by middleware. |
| Manifest `integrity` (SRI) | When your Vite build populates `integrity` hashes in `manifest.json` (e.g. via `vite-plugin-manifest-sri`), `ViteAssetLoader` automatically propagates `integrity="sha384-..."` and `crossorigin="anonymous"` onto `<script>`, `<link rel="stylesheet">`, and `<link rel="modulepreload">` tags. |

Internal build metadata (`manifest.json`, `.vite/manifest.json`, `ssr-manifest.json`, `.litestar.json`, and the `hot` file) returns `404` from the Litestar static route regardless of these settings.

!!! note "Granian Native Static Placement (`StaticPlacement.NATIVE`)"
    The built-in asset hardening (`immutable_cache_headers` and `404` blocking for `manifest.json` / `.vite/manifest.json` / `hot`) is implemented as picklable router-level hooks (`_StaticBeforeRequestHook`, `_StaticAfterRequestHook`) so `StaticFilesConfig.has_asgi_overrides()` stays `False` and the bundle remains eligible for Granian native serving. Consequently, router hooks do not execute on Granian-native hits — configure equivalent cache headers and metadata blocking at the reverse proxy or CDN layer when relying on `StaticPlacement.NATIVE`.

---

## Deploying Bundles to S3, GCS, or Cloudflare R2

When `DeployConfig` is configured (or `--storage` / `VITE_DEPLOY_STORAGE` is set), `litestar assets deploy` runs `vite build` (unless `--no-build` is passed), uploads your compiled `bundle_dir` to any [`fsspec`](https://filesystem-spec.readthedocs.io/) storage backend, and prunes orphaned files:

```bash
litestar assets deploy --storage s3://my-app-assets-prod/assets --storage-option region_name=us-east-1
```

Use `--dry-run` in CI pull requests to preview which hashed files would be uploaded or deleted without mutating remote storage:

```bash
litestar assets deploy --dry-run
```
