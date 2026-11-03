# Migrating to v0.33

Version 0.33 makes production SSR bundles self-contained, adds native Deno/Bun runtime auto-detection and PEP 425 wheel extras, hardens static asset headers, and introduces an experimental in-process QuickJS SSR transport (`WasmIPCTransport`). Review these points before upgrading applications that use Inertia SSR or server-side fragments.

---

## Self-Contained SSR Bundles (`ssr.noExternal`)

The npm plugin now sets `ssr.noExternal: true` when building the production SSR bundle (`ssrOutputDir`). Every dependency imported by the SSR entry is inlined into `ssr.js` so the worker can run under Node, Bun, Deno, or the in-process QuickJS transport (`WasmIPCTransport`) without a `node_modules` directory present on the production host.

Projects that intentionally kept packages external — for example to share a native-module dependency or to keep `ssr.js` small — can restore the previous behavior in `vite.config.ts`:

```typescript title="vite.config.ts"
import { defineConfig } from "vite";

export default defineConfig({
  ssr: {
    noExternal: [],
  },
});
```

Explicit user `ssr.noExternal` values always win over the plugin default.

Packages that cannot be bundled (native Node addons, packages that rely on `__dirname`-relative file access) must stay external and therefore require a host JavaScript runtime; they are incompatible with `WasmIPCTransport`.

---

## SSR Worker Lifecycle (`startSsrWorker`)

`startSsrWorker` from `litestar-vite-plugin/ssr-worker` no longer imports `node:readline`. It reads `process.stdin` with a streaming UTF-8 `TextDecoder`, registers `globalThis.__litestar_ssr_dispatch__` for in-process engines, and exits with status `0` after `stdin` reaches EOF and in-flight renders have completed.

Custom SSR entrypoints that previously attached their own `readline` interface should migrate to `startSsrWorker` so the same entry runs on every runtime:

```tsx title="resources/ssr.tsx"
import { createInertiaApp } from "@inertiajs/react";
import ReactDOMServer from "react-dom/server";
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers";
import { startSsrWorker } from "litestar-vite-plugin/ssr-worker";

export default function render(page: unknown) {
  return createInertiaApp({
    page: page as never,
    render: ReactDOMServer.renderToString,
    resolve: (name: string) =>
      resolvePageComponent(
        `./pages/${name}.tsx`,
        import.meta.glob("./pages/**/*.tsx", { eager: true }),
      ),
    setup: ({ App, props }: { App: any; props: any }) => <App {...props} />,
  });
}

startSsrWorker({ render });
```

---

## Static Asset Behavior & Headers

Litestar's production static route now returns `404` for internal build metadata (`manifest.json`, `.vite/manifest.json`, `ssr-manifest.json`, `.litestar.json`, `hot`) and sets `Cache-Control: public, max-age=31536000, immutable` on content-hashed files under the Vite `assets` directory.

- Set `RuntimeConfig(immutable_cache_headers=False)` to keep the previous headers.
- Set `RuntimeConfig(link_preload_headers=False)` to disable automatic RFC 8288 `Link` preload headers on HTML responses.
- Because these hooks are attached at the `Router` level to preserve `StaticPlacement.NATIVE` eligibility, they are **not applied when Granian serves assets natively**; configure equivalent cache headers and metadata blocking at the server or CDN layer in that deployment.
