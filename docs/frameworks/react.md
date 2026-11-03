# React

Build React applications with Litestar using Vite 7+, `@vitejs/plugin-react` Fast Refresh, automatic OpenAPI + route type generation, and reactive realtime hooks.

---

## Quick Start

Scaffold a React project with `litestar assets init`:

=== "React SPA"

    ```bash
    litestar assets init --template react
    litestar assets install
    litestar run --reload
    ```

=== "React + Inertia"

    ```bash
    litestar assets init --template react-inertia
    litestar assets install
    litestar run --reload
    ```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar application
├── index.html              # SPA HTML shell (root or resources/)
├── package.json
├── tsconfig.json
├── vite.config.ts          # Vite + @vitejs/plugin-react + litestar-vite-plugin
└── src/
    ├── main.tsx            # React root entrypoint
    ├── App.tsx             # Root component
    └── generated/          # Auto-generated routes.ts, schemas.ts, api/, channels.ts
```

---

## Configuration

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Summary(Struct):
        title: str
        headline: str


    @get("/api/summary", name="summary", sync_to_thread=False)
    def get_summary() -> Summary:
        """Return typed summary payload."""
        return Summary(title="Litestar + React", headline="Fast Refresh & End-to-End Types")


    app = Litestar(
        route_handlers=[get_summary],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="spa",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("src")),
                    runtime=RuntimeConfig(is_react=True),
                    types=TypeGenConfig(generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Vite (`vite.config.ts`)"

    ```typescript title="vite.config.ts"
    import path from "node:path";
    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        react(),
        litestar({
          input: ["src/main.tsx"],
          types: "auto",
        }),
      ],
      resolve: {
        alias: {
          "@": path.resolve(__dirname, "./src"),
        },
      },
    });
    ```

=== "HTML Entry (`index.html`)"

    ```html title="index.html"
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Litestar + React</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.tsx"></script>
      </body>
    </html>
    ```

---

## React Fast Refresh Preamble

Unlike Vue and Svelte, `@vitejs/plugin-react` requires an inline `<script type="module">` Fast Refresh preamble (`/@react-refresh`) in `<head>` before any `.tsx` or `.jsx` module executes in development:

- **Automatic Detection**: When `litestar-vite-plugin` detects `@vitejs/plugin-react` (or `@vitejs/plugin-react-swc`) in `vite.config.ts`, or when `RuntimeConfig(is_react=True)` is set in Python, `ViteAssetLoader.render_hmr_client()` and the SPA HTML transformer inject the React Fast Refresh preamble automatically.
- **Zero Production Overhead**: In production (`dev_mode=False`), no preamble is emitted.

---

## Consuming Generated Types & Routes

With `types=True` (or `TypeGenConfig()`), Litestar Vite generates both `routes.ts` and the `@hey-api/openapi-ts` client SDK under `src/generated/`:

```tsx title="src/App.tsx"
import { useEffect, useState } from "react";
import { route } from "@/generated/routes";
import { getApiSummary, type Summary } from "@/generated/api";

export function App() {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    getApiSummary().then(({ data }: { data?: Summary }) => {
      if (data) setSummary(data);
    });
  }, []);

  if (!summary) return <p>Loading from {route("summary")}...</p>;

  return (
    <main>
      <h1>{summary.title}</h1>
      <p>{summary.headline}</p>
    </main>
  );
}
```

---

## Realtime & Event Stream Hooks

Import `useEventStream` or `useQueueEventStream` from `litestar-vite-plugin/react` to subscribe to Server-Sent Events or Litestar Channels in React components with automatic reconnection and cleanup on unmount:

```tsx title="src/Notifications.tsx"
import { useEventStream } from "litestar-vite-plugin/react";

interface NotificationPayload {
  id: string;
  message: string;
}

export function Notifications() {
  const { healthy, lastEvent } = useEventStream<NotificationPayload>({
    key: "notifications",
    url: "/api/notifications/stream",
    onEvent: () => {},
  });

  return (
    <aside>
      <span>Stream healthy: {String(healthy)}</span>
      {lastEvent && <p>{lastEvent.message}</p>}
    </aside>
  );
}
```

See [Realtime Event Streams](../typegen/event-streams.md) for typed AsyncAPI channels, authentication tickets, and gap recovery.
