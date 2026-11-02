# Development Server & Single-Port Proxy

During local development (`dev_mode=True`), Litestar Vite manages the Vite child process inside Litestar's ASGI lifespan and streams all Vite module requests and HMR WebSockets through your single Litestar port (`http://127.0.0.1:8000`).

<!-- termynal -->

```console
$ litestar run --reload
INFO:     Exported .litestar.json, openapi.json, and routes.json
INFO:     Starting Vite dev server (npm run dev)...
INFO:     Vite listening on http://127.0.0.1:5173 (hotfile written)
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## Lifespan Process Supervision & Crash Recovery

When `RuntimeConfig(start_dev_server=True)` (the default when `dev_mode=True`), `VitePlugin.lifespan()` spawns and supervises the Vite dev server automatically:

1. **Startup Handshake**: Before spawning Vite, Litestar writes `.litestar.json` and exports OpenAPI/route schemas.
2. **Dynamic Port Discovery**: `litestar-vite-plugin` binds a free port and writes its bound URL (`http://127.0.0.1:5173`) to `<bundle_dir>/hot`.
3. **Capped Exponential Backoff**: If the Vite process exits unexpectedly (e.g., due to a syntax error in `vite.config.ts`), the lifespan supervisor restarts it with capped exponential backoff (`0.5s` up to `8.0s`).

### Two-Terminal Manual Workflow

If you prefer running `npm run dev` (or `litestar assets serve`) in a separate terminal tab, set `RuntimeConfig(start_dev_server=False)`. `ViteProxyMiddleware` still reads `<bundle_dir>/hot` dynamically so single-port proxying continues to work seamlessly.

---

## Proxy Modes

`RuntimeConfig.proxy_mode` (or the `VITE_PROXY_MODE` environment variable) controls which paths `ViteProxyMiddleware` forwards to the Vite dev server:

| Proxy Mode | Default For | Forwarding Rule |
| --- | --- | --- |
| **`proxy_mode="vite"`** (Allowlist) | `mode="spa"`, `mode="hybrid"`, `mode="template"` | Forwards **only** Vite internal paths (`/@vite/client`, `/@react-refresh`, `/@fs/*`, `/@id/*`, `/node_modules/*`), source entrypoints under `resource_dir`, and HMR WebSockets (`/static/vite-hmr`). Litestar handles all application routes (`/` and `/api/*`). |
| **`proxy_mode="proxy"`** (Denylist) | `mode="framework"` (`ssr`/`ssg`), `mode="external"` | Forwards every request that **does not** match a registered Litestar route or `RuntimeConfig.extra_route_prefixes` to the meta-framework dev server (Astro, Nuxt, SvelteKit, Angular CLI). |
| **`proxy_mode=None`** | Disabled | Disables `ViteProxyMiddleware` when an external reverse proxy (Caddy, Nginx, Traefik) fronts both servers. |

---

## Protecting Backend Prefix Routes

In `mode="spa"` (which registers a catch-all `/{path:path}` route for client-side routing) and `proxy_mode="proxy"`, `RuntimeConfig(extra_route_prefixes=...)` ensures backend-only prefixes never fall through to the SPA shell or meta-framework proxy when a specific URL 404s:

```python
from litestar_vite import RuntimeConfig, ViteConfig

config = ViteConfig(
    mode="spa",
    dev_mode=True,
    runtime=RuntimeConfig(
        extra_route_prefixes=("/api", "/schema", "/admin", "/health"),
    ),
)
```

With `extra_route_prefixes` configured, a request to `/api/nonexistent` returns a proper Litestar 404 Not Found JSON response instead of serving `index.html`.

---

## Same-Origin Guarantee in Development

Because the browser only ever communicates with `http://127.0.0.1:8000` (both for HTML/API requests and `/static/vite-hmr` WebSocket upgrades):

- `HttpOnly` session cookies and `SameSite=Lax` / `SameSite=Strict` CSRF cookies work without relaxed development CORS policies.
- Relative `fetch("/api/...")` and `EventSource("/api/...")` calls resolve against the exact same origin in development and production.
