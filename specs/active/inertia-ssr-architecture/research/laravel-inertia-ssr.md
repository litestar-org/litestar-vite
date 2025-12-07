# Laravel/Inertia SSR Architecture Research

## Overview

Inertia.js provides two rendering modes:
1. **Client-Side Rendering (CSR)** - Default, browser loads JS and renders
2. **Server-Side Rendering (SSR)** - Node.js pre-renders pages for SEO/performance

## How CSR Works (Current litestar-vite Implementation)

```
┌─────────┐     /page        ┌─────────────┐
│ Browser │ ────────────────>│  Litestar   │
│         │<──────────────── │  (Python)   │
│         │   HTML + props   │             │
│         │                  │             │
│         │  /static/*.js    │             │
│         │ ────────────────>│ Static/Proxy│──> Serve from bundle or Vite dev
│         │<──────────────── │             │
│         │   JS bundles     │             │
└─────────┘                  └─────────────┘

Browser loads JS → React/Vue hydrates with props from data-page attribute
```

## How SSR Works (Laravel Implementation)

### Architecture Diagram

```
┌─────────┐     /page        ┌─────────────┐  HTTP POST    ┌─────────────┐
│ Browser │ ────────────────>│  Laravel    │──────────────>│ Node.js SSR │
│         │                  │  (PHP)      │               │ (port 13714)│
│         │                  │             │<──────────────│             │
│         │<──────────────── │             │  Rendered HTML│             │
│         │  Full HTML +     └─────────────┘               └─────────────┘
│         │  hydration data
│         │
│         │  /static/*.js
│         │ ────────────────>  Static File Server
│         │<────────────────   (built bundles)
└─────────┘
```

### Key Components

1. **SSR Entry Point** (`resources/js/ssr.js`)
   ```javascript
   import { createInertiaApp } from '@inertiajs/vue3'
   import createServer from '@inertiajs/vue3/server'
   import { renderToString } from '@vue/server-renderer'

   createServer((page) =>
       createInertiaApp({
           page,
           render: renderToString,
           resolve: name => resolvePageComponent(name, import.meta.glob('./Pages/**/*.vue')),
           setup({ App, props, plugin }) {
               return createSSRApp({ render: () => h(App, props) })
                   .use(plugin)
           },
       })
   )
   ```

2. **SSR Server Configuration**
   - Default port: 13714
   - Configurable via `createServer(callback, { port: 13715 })`
   - Supports clustering for multi-core: `createServer(callback, { cluster: true })`

3. **Laravel Configuration** (`config/inertia.php`)
   ```php
   'ssr' => [
       'enabled' => env('INERTIA_SSR_ENABLED', true),
       'url' => env('INERTIA_SSR_URL', 'http://127.0.0.1:13714/render'),
   ],
   ```

4. **Communication Protocol**
   - Laravel POST to `http://127.0.0.1:13714/render`
   - Request body: JSON with `{ component, props, url, version }`
   - Response: Rendered HTML string

### Build Process

```bash
# Build both client and SSR bundles
npm run build  # runs: vite build && vite build --ssr

# Start SSR server
php artisan inertia:start-ssr

# Or with Bun runtime
php artisan inertia:start-ssr --runtime=bun
```

### Health & Management Commands

```bash
# Check if SSR server is running
php artisan inertia:check-ssr

# Stop SSR server gracefully
php artisan inertia:stop-ssr
```

## Implications for litestar-vite

### Current State
- CSR mode works (with the proxy bug fixed)
- No SSR support

### For Future SSR Support

1. **New Configuration**
   ```python
   class SSRConfig:
       enabled: bool = False
       url: str = "http://127.0.0.1:13714/render"
       timeout: float = 5.0
       bundle_check: bool = True  # Check if SSR bundle exists
   ```

2. **SSR Client Implementation**
   ```python
   async def render_ssr(self, component: str, props: dict, url: str) -> str:
       async with httpx.AsyncClient() as client:
           response = await client.post(
               self.config.ssr.url,
               json={"component": component, "props": props, "url": url},
               timeout=self.config.ssr.timeout,
           )
           return response.text
   ```

3. **Integration Point**
   - Hook into InertiaResponse.to_response()
   - If SSR enabled, call SSR server before returning response
   - Inject rendered HTML into template

### Alternatives to Node.js SSR

1. **Cloudflare Workers** - Run SSR at edge locations
2. **Bun Runtime** - Faster alternative to Node.js (supported via `--runtime=bun`)
3. **No SSR** - For apps where SEO isn't critical, CSR is simpler

## References

- [Inertia.js SSR Docs](https://inertiajs.com/server-side-rendering)
- [Fly.io Inertia SSR Guide](https://fly.io/docs/laravel/advanced-guides/using-inertia-ssr/)
- [Changing SSR Port](https://laravel.io/articles/how-to-change-the-default-ssr-port-for-inertiajs)
- [Cloudflare Workers SSR](https://geisi.dev/blog/deploying-inertia-vue-ssr-to-cloudflare-workers/)
