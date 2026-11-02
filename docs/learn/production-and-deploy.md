# Production Builds, Granian Native Static & CDN Deployment

Moving a `litestar-vite` application from development to production swaps the live Vite dev proxy for pre-compiled, content-hashed bundles (`manifest.json`), optional Rust-level static serving with Granian (`StaticPlacement.NATIVE`), single-binary PyApp packaging (`litestar assets bundle`), and one-command cloud storage uploads (`litestar assets deploy`).

--8<-- "tools/docs/includes/diagram-dev-vs-prod.html"

---

## 1. Building Production Bundles (`litestar assets build`)

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

## 2. Production `ViteConfig` & Granian Native Static Serving

In production (`dev_mode=False`), `ViteAssetLoader` reads `manifest.json` once at startup and resolves asset tags with O(1) dictionary lookups.

When paired with [`litestar-granian`](https://github.com/litestar-org/litestar-granian) (`GranianPlugin(static="auto")`), `VitePlugin` exposes a [`StaticServerConfig`](../reference/runtime-and-assets.md#litestar_vite.plugin.StaticServerConfig) contract (`StaticPlacement.NATIVE`) so Granian's Rust HTTP worker serves hashed bundle files directly before the request ever enters Python or ASGI:

```python title="docs/examples/learn/production_deploy.py"
--8<-- "docs/examples/learn/production_deploy.py"
```

### Server & Static Placement Matrix

| ASGI Server | Static Serving Mechanism | Metadata Blocking (`manifest.json`, `hot`) | Immutable Cache Headers |
| --- | --- | --- | --- |
| **Granian (`StaticPlacement.NATIVE`)** | Rust HTTP worker serves static files before Python/ASGI | Enforced via native path exclusions + `_StaticBeforeRequestHook` | `Cache-Control: public, max-age=31536000, immutable` |
| **Uvicorn / Hypercorn (`StaticPlacement.ASGI`)** | Litestar `create_static_files_router` | Enforced via `_StaticBeforeRequestHook` (`404 Not Found`) | Enforced via `_StaticAfterRequestHook` |

---

## 3. Single-File Executable Packaging (`litestar assets bundle`)

Use `litestar assets bundle` with `[tool.litestar.bundle]` in `pyproject.toml` to package your Litestar application, compiled Vite frontend assets, `python-build-standalone` runtime, and optional compiled SSR worker into a self-contained native executable via [PyApp](https://ofek.dev/pyapp/):

```toml title="pyproject.toml"
[tool.litestar.bundle]
project_name = "my-app"
exec_module = "app:main"
python_version = "3.12"
include_assets = true
compile_ssr = false
```

```bash
litestar assets bundle --platform linux-x86_64
```

---

## 4. Deploying Bundles to S3, GCS, or Cloudflare R2 (`litestar assets deploy`)

When `DeployConfig` is configured (or `VITE_DEPLOY_STORAGE` is set), `litestar assets deploy` uploads your compiled `bundle_dir` to any [`fsspec`](https://filesystem-spec.readthedocs.io/) storage backend and prunes orphaned files:

```bash
litestar assets deploy --storage s3://my-app-assets-prod/assets --asset-url https://cdn.example.com/assets/
```

Use `--dry-run` in CI pull requests to preview which hashed files would be uploaded or deleted without mutating remote storage:

```bash
litestar assets deploy --dry-run
```
