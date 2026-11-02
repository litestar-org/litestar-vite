---
title: Dev Proxy & .litestar.json Bridge
description: How Litestar and Vite 7+ coordinate via .litestar.json, the hot file, and the single-port AnyIO HTTP/WebSocket proxy.
---

# Dev Proxy & `.litestar.json` Bridge

Running two separate servers during development (`localhost:8000` for Python and `localhost:5173` for Vite) traditionally introduces CORS configuration drift, split cookie origins, and broken WebSocket HMR paths behind reverse proxies. `litestar-vite` eliminates two-port friction with a **single-port AnyIO streaming proxy** and a deterministic **`.litestar.json` configuration bridge**.

--8<-- "tools/docs/includes/diagram-dev-proxy.html"

---

## The `.litestar.json` Handshake

Python (`ViteConfig`) is the single source of truth for asset paths, ports, executors, and type-generation flags.

1. **Python Startup (`VitePlugin.on_app_init`)**: Before launching or connecting to Vite, `VitePlugin` serializes resolved paths (`bundleDir`, `resourceDir`, `staticDir`, `assetUrl`, `hotFile`, `manifest`), runtime settings (`mode`, `proxyMode`, `host`, `port`, `executor`, `litestarPort`), typegen settings (`types`), and static props (`staticProps`) into `.litestar.json`.
2. **Vite Startup (`readBridgeConfig`)**: In `vite.config.ts`, `litestar({ input: ["src/main.ts"] })` reads `.litestar.json` via `readBridgeConfig()`. You never have to repeat `bundleDir`, `assetUrl`, or `types.output` in TypeScript.
3. **Ephemeral Port Discovery (`hot` file)**: Once Vite's HTTP server binds to its port, `litestar-vite-plugin` writes the active dev server URL (for example `http://127.0.0.1:5173`) to `${bundleDir}/${hotFile}` (`public/hot` by default) and removes the file automatically on process exit (`SIGINT`, `SIGTERM`, `SIGHUP`).

---

## Single-Port AnyIO Streaming Proxy (`ViteProxyMiddleware`)

When `runtime.dev_mode=True` and `proxy_mode="vite"` (the default), browser clients connect **exclusively** to the Litestar port (`http://127.0.0.1:8000`):

- **Zero Runtime HTTPX Dependency**: `ViteProxyMiddleware` uses raw `anyio.connect_tcp` sockets for HTTP/1.1 request/response streaming and `wsproto` for WebSocket frame tunneling (`vite-hmr`), keeping the core package lightweight.
- **Dynamic Target Resolution**: On each proxied request, `ViteProxyMiddleware` reads the target host and port from the `hot` file (caching by mtime), so if Vite restarts on a new port, Litestar routes to the new port without restarting Python.
- **HMR WebSocket Tunneling (`/static/vite-hmr`)**: `litestar-vite-plugin` configures Vite's HMR channel (`server.ws` on Vite 8.1+ / `server.hmr` on Vite 7) with `path: "vite-hmr"`, which Vite prefixes with `assetUrl` (`/static/vite-hmr`). `ViteProxyMiddleware` intercepts WebSocket upgrades on that path and tunnels frames bidirectionally between the browser and Vite.
- **HTML Transformation (`/__litestar__/transform-index`)**: In SPA mode, `AppHandler` delegates dev-time HTML entry transformation to Vite's internal middleware pipeline (`server.transformIndexHtml`) and injects `window.__LITESTAR_CSRF__` before returning the HTML shell.

---

## Production Static Serving & Granian `StaticPlacement.NATIVE`

When `dev_mode=False`, `ViteProxyMiddleware` is not mounted. Instead, `VitePlugin` registers static file serving for `bundle_dir` and `static_dir` with two Router-level hooks:

| Hook Class | Responsibility | Why Attached at Router Level |
| :--- | :--- | :--- |
| `_StaticBeforeRequestHook` | Returns `404 Not Found` for build metadata files (`manifest.json`, `.vite/manifest.json`, `ssr-manifest.json`, `hot`). | Keeps `StaticFilesConfig.has_asgi_overrides()` equal to `False` so `litestar-granian` can serve static files directly inside Rust (`StaticPlacement.NATIVE`). |
| `_StaticAfterRequestHook` | Sets `Cache-Control: public, max-age=31536000, immutable` on hashed bundle paths (`/static/assets/*`). | Picklable slotted callable class (`__slots__`) that survives `copy.deepcopy(router)` during Litestar route registration. |
