# Migrating to v0.32

Litestar Vite v0.32.0 unifies the SSR and fragment IPC transport layer, upgrades the minimum Vite peer dependency to **Vite 7+**, and consolidates AsyncAPI 3.0 schema ownership on `litestar-asyncapi`.

---

## Lockstep Python & npm Version Upgrade

Always upgrade the Python `litestar-vite` package and the npm `litestar-vite-plugin` package together so `.litestar.json` bridge contracts match:

=== "uv + npm"

    ```bash
    uv add "litestar-vite>=0.32.0"
    npm install -D "litestar-vite-plugin@^0.32.0" "vite@^7.0.0"
    ```

=== "pip + pnpm"

    ```bash
    pip install -U "litestar-vite>=0.32.0"
    pnpm add -D "litestar-vite-plugin@^0.32.0" "vite@^7.0.0"
    ```

---

## SSR Transport Simplification

Prior to 0.32.0, Inertia SSR spawned a standalone HTTP server (`node ssr.js` listening on port `13714`) and polled a `/health` endpoint. In 0.32.0, SSR uses two zero-configuration IPC transports:

- **Development (`dev_mode=True`)**: `TCPStreamIPCTransport` connects directly to Vite's `/__litestar_ssr__` endpoint (`ModuleRunner`). No separate SSR server port or build is required in development.
- **Production (`dev_mode=False`)**: `StdioIPCTransport` streams newline-delimited JSON over `stdin`/`stdout` pipes to a managed worker subprocess.

### Removed SSR Configuration Fields

| Pre-0.32 Field | 0.32.0 Replacement |
| --- | --- |
| `InertiaSSRConfig(url="http://127.0.0.1:13714/render")` | **Removed** — Dev uses Vite's hotfile (`/__litestar_ssr__`); production uses `StdioIPCTransport` (`InertiaSSRConfig.command` / `RuntimeConfig.ssr_command`). |
| `InertiaSSRConfig(auto_start=True)` | **Removed** — Worker lifecycle is managed automatically by `InertiaPlugin.lifespan()`. |
| `InertiaSSRConfig(health_check=True)` | **Removed** — `SSRCircuitBreaker` tracks worker health per IPC call without HTTP polling. |
| `InertiaSSRConfig(enabled=True, timeout=2.0, fallback_to_client=True)` | **Supported** — Configure `enabled`, `timeout`, `target_selector`, `command`, `cwd`, `fallback_to_client`, and `circuit_breaker_*`. |

---

## Dual-Mode SSR Entrypoint

Update your SSR entrypoint so it both exports `default function render(page)` (consumed by Vite's `ModuleRunner` in development) and calls `startSsrWorker({ render })` (consumed by `StdioIPCTransport` in production):

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

## AsyncAPI Channel Codegen

In 0.32.0, `TypeGenConfig(generate_channels=True)` requires a registered `litestar_asyncapi.AsyncAPIPlugin` on your `Litestar` application (`uv add "litestar-vite[asyncapi]"`):

- `litestar-asyncapi` owns AsyncAPI 3.0 schema extraction across WebSockets, `ChannelsPlugin`, and SSE routes.
- `litestar_vite.codegen` normalizes the exported `asyncapi.json` document (`normalize_asyncapi_document`) and generates `src/generated/channels.ts`.
