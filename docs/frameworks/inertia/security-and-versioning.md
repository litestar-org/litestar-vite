# Security, History Encryption & Asset Versioning

This guide covers CSRF protection with `cookie_httponly=True`, encrypting sensitive `window.history.state` payloads, and zero-downtime asset versioning across rolling deployments.

---

## CSRF Protection

Litestar's `CSRFConfig` protects state-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`). Litestar Vite supports `CSRFConfig(cookie_httponly=True)` out of the box by injecting the CSRF token into `props.csrf_token` (in Inertia mode) and `window.__LITESTAR_CSRF__` (in SPA mode) so JavaScript never needs to read `document.cookie`:

```python title="app.py"
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar_vite import InertiaConfig, ViteConfig, VitePlugin

app = Litestar(
    route_handlers=[],
    csrf_config=CSRFConfig(
        secret="replace-with-32-byte-production-secret",
        cookie_httponly=True,
        header_name="x-csrf-token",
    ),
    plugins=[
        VitePlugin(config=ViteConfig(mode="hybrid", inertia=InertiaConfig())),
    ],
)
```

### Automatic CSRF Header Injection

Import `csrfHeaders`, `getCsrfToken`, or `csrfFetch` from `litestar-vite-plugin/helpers` and configure Inertia's `visitOptions` so every non-GET visit includes the `X-CSRF-Token` header automatically:

```typescript title="resources/main.ts"
import { csrfHeaders, csrfFetch, getCsrfToken } from "litestar-vite-plugin/helpers";

// 1. Inside createInertiaApp({ defaults: { ... } }):
const defaults = {
  visitOptions: (_href: string, options: { headers?: Record<string, string> }) => ({
    headers: csrfHeaders(options.headers ?? {}),
  }),
};

// 2. For standalone fetch() requests outside Inertia:
async function pingAction() {
  const token = getCsrfToken();
  return csrfFetch("/api/ping", { method: "POST", headers: { "X-Requested-With": token } });
}
```

### Token Resolution Order

`getCsrfToken()` resolves the active token deterministically in this order:

1. `window.__LITESTAR_CSRF__` (injected by the SPA HTML transformer)
2. `<meta name="csrf-token" content="...">` (used in Jinja2 / HTMX templates)
3. `<script type="application/json" id="app_page" data-page="app">` (`props.csrf_token`)
4. `<div id="app" data-page="...">` (`props.csrf_token`)

---

## History Encryption

By default, Inertia caches each visited page's `PageProps` inside the browser's `window.history.state` so pressing the **Back** button restores the page instantaneously. If your application displays sensitive data (financial records, PII, medical charts) on shared computers, enable **History Encryption** so cached state is encrypted with AES-GCM via the browser's Web Crypto API and wiped upon logout:

```python
from typing import Any
from litestar import Request, get, post
from litestar_vite.inertia import InertiaRedirect, InertiaResponse, clear_history


@get("/billing/statements", component="Billing/Statements", sync_to_thread=False)
def view_statements() -> InertiaResponse[dict[str, Any]]:
    """Encrypt history state for this specific sensitive route."""
    return InertiaResponse(
        {"statements": [{"id": 1, "amount": "$420.00"}]},
        encrypt_history=True,
    )


@post("/logout", name="logout", sync_to_thread=False)
def logout_user(request: Request[Any, Any, Any]) -> InertiaRedirect:
    """Clear user session and rotate browser history encryption keys."""
    request.session.clear()
    clear_history(request)
    return InertiaRedirect(request, redirect_to="/login")
```

- **Global Encryption**: Set `InertiaConfig(encrypt_history=True)` to encrypt history state across all Inertia responses.
- **HTTPS / Secure Context Requirement**: History encryption uses `window.crypto.subtle`, which requires either `https://` in production or `http://localhost` / `http://127.0.0.1` in development.

---

## Asset Versioning & Rolling Deployments

In a single-page app, users can keep a browser tab open for hours or days. When you deploy a new frontend bundle:

1. `ViteAssetLoader.version_id` computes a deterministic SHA-256 digest of your `manifest.json` (in production) or `"1.0"` (in development).
2. Every Inertia visit sends `X-Inertia-Version: <version_id>`.
3. If a `GET` request arrives with an outdated `X-Inertia-Version`, `InertiaMiddleware` responds with 409 Conflict and `X-Inertia-Location: <request.url>`.
4. The Inertia client intercepts the 409 response and transparently performs a full `window.location` reload so the browser downloads the newly deployed JS/CSS bundles.
