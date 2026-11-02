# Svelte 5

Build Svelte 5 applications with Litestar using fine-grained runes (`$state`, `$derived`, `$effect`, `$props`), Vite 7+ HMR, and automatic TypeScript code generation.

---

## Quick Start

Scaffold a Svelte 5 project with `litestar assets init`:

=== "Svelte 5 SPA"

    ```bash
    litestar assets init --template svelte
    litestar assets install
    litestar run --reload
    ```

=== "Svelte 5 + Inertia"

    ```bash
    litestar assets init --template svelte-inertia
    litestar assets install
    litestar run --reload
    ```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar application
├── index.html              # SPA HTML shell
├── package.json
├── svelte.config.js        # vitePreprocess configuration
├── tsconfig.json
├── vite.config.ts          # Vite + @sveltejs/vite-plugin-svelte + litestar-vite-plugin
└── src/
    ├── main.ts             # Svelte 5 mount(App, ...) entrypoint
    ├── App.svelte          # Root Svelte 5 component
    └── generated/          # Auto-generated routes.ts, schemas.ts, api/, channels.ts
```

---

## Configuration

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Summary(Struct):
        title: str
        headline: str


    @get("/api/summary", name="summary", sync_to_thread=False)
    def get_summary() -> Summary:
        """Return typed summary payload."""
        return Summary(title="Litestar + Svelte 5", headline="Runes & End-to-End Types")


    app = Litestar(
        route_handlers=[get_summary],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="spa",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("src")),
                    types=TypeGenConfig(generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Vite (`vite.config.ts`)"

    ```typescript title="vite.config.ts"
    import { defineConfig } from "vite";
    import { svelte } from "@sveltejs/vite-plugin-svelte";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        svelte(),
        litestar({
          input: ["src/main.ts"],
          types: "auto",
        }),
      ],
    });
    ```

=== "Svelte 5 Entry (`src/main.ts`)"

    ```typescript title="src/main.ts"
    import { mount } from "svelte";
    import App from "./App.svelte";

    const target = document.getElementById("app");
    if (!target) {
      throw new Error("Root element #app not found");
    }

    export default mount(App, { target });
    ```

---

## Svelte 5 Runes with Generated Types

Svelte 5 components use `$state`, `$derived`, `$effect`, and `$props()` alongside generated `route()` and SDK functions:

```svelte title="src/App.svelte"
<script lang="ts">
  import { route } from "./generated/routes";
  import { getApiSummary, type Summary } from "./generated/api";

  let summary = $state<Summary | null>(null);
  let loading = $state(true);
  const endpointUrl = route("summary");

  $effect(() => {
    getApiSummary().then(({ data }: { data?: Summary }) => {
      if (data) summary = data;
      loading = false;
    });
  });
</script>

{#if loading}
  <p>Loading from {endpointUrl}...</p>
{:else if summary}
  <main>
    <h1>{summary.title}</h1>
    <p>{summary.headline}</p>
  </main>
{/if}
```

---

## Realtime Stores (`litestar-vite-plugin/svelte`)

`litestar-vite-plugin/svelte` exports Svelte-compatible readable stores (`createEventStreamStore` and `createQueueEventStreamStore`) that automatically connect on first subscriber (`$store`) and close when the last subscriber unsubscribes:

```svelte title="src/Notifications.svelte"
<script lang="ts">
  import { createEventStreamStore } from "litestar-vite-plugin/svelte";

  interface NotificationPayload {
    id: string;
    message: string;
  }

  const stream = createEventStreamStore<NotificationPayload>({
    url: "/api/notifications/stream",
    onEvent: () => {},
  });
</script>

<aside>
  <span>Healthy: {$stream.healthy}</span>
  {#if $stream.lastEvent}
    <p>{$stream.lastEvent.message}</p>
  {/if}
</aside>
```

See [Realtime Event Streams](../typegen/event-streams.md) for typed AsyncAPI channels and stream presets.
