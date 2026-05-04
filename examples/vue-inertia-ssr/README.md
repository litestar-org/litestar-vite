# Vue + Inertia.js + SSR

Hybrid mode (`mode="hybrid"`, auto-derived) with Inertia server-side rendering.
The Inertia handler frame POSTs the page payload to the Node SSR server at
`http://127.0.0.1:13714/render`; Litestar injects the returned `head` and `body`
into the SPA shell before sending it back to the browser.

## Run (two processes)

```bash
# Terminal 1 — build the SSR bundle once, then start the Node /render server
litestar --app-dir examples/vue-inertia-ssr assets install
npm --prefix examples/vue-inertia-ssr run build:ssr
npm --prefix examples/vue-inertia-ssr run start:ssr

# Terminal 2 — start Litestar (auto-starts Vite dev server)
litestar --app-dir examples/vue-inertia-ssr run
```

## What it demonstrates

- `InertiaConfig(ssr=True)` enables the POST-to-13714 SSR pipeline
- `resources/ssr.ts` runs `createServer((page) => createInertiaApp(...))` from
  `@inertiajs/vue3/server` + `@vue/server-renderer`'s `renderToString`
- `createSSRApp` on the client matches the SSR-rendered tree for hydration
- The Inertia SSR HTTP path is **independent** of the dev `proxy_mode`; the
  browser still only ever sees the Litestar port
