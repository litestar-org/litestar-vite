# Vue 3

Build Vue 3 applications with Litestar using Single-File Components (`.vue`), the Composition API (`<script setup lang="ts">`), Vite 7+ HMR, and end-to-end TypeScript codegen.

---

## Quick Start

Scaffold a Vue 3 project with `litestar assets init`:

=== "Vue 3 SPA"

    ```bash
    litestar assets init --template vue
    litestar assets install
    litestar run --reload
    ```

=== "Vue 3 + Inertia"

    ```bash
    litestar assets init --template vue-inertia
    litestar assets install
    litestar run --reload
    ```

=== "Vue 3 + Inertia SSR"

    ```bash
    litestar assets init --template vue-inertia-ssr
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
├── tsconfig.json
├── vite.config.ts          # Vite + @vitejs/plugin-vue + litestar-vite-plugin
└── src/
    ├── main.ts             # Vue createApp entrypoint
    ├── App.vue             # Root Single-File Component
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
        return Summary(title="Litestar + Vue 3", headline="Composition API & Typed Routes")


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
    import path from "node:path";
    import { defineConfig } from "vite";
    import vue from "@vitejs/plugin-vue";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        vue(),
        litestar({
          input: ["src/main.ts"],
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

=== "Vue Entry (`src/main.ts`)"

    ```typescript title="src/main.ts"
    import { createApp } from "vue";
    import App from "./App.vue";

    createApp(App).mount("#app");
    ```

---

## Single-File Component with Generated Types

Use `<script setup lang="ts">` to import generated routes (`route()`) and OpenAPI SDK functions directly inside `.vue` components:

```vue title="src/App.vue"
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { route } from "@/generated/routes";
import { getApiSummary, type Summary } from "@/generated/api";

const summary = ref<Summary | null>(null);
const endpointUrl = route("summary");

onMounted(async () => {
  const { data } = await getApiSummary();
  if (data) {
    summary.value = data;
  }
});
</script>

<template>
  <main v-if="summary">
    <h1>{{ summary.title }}</h1>
    <p>{{ summary.headline }}</p>
  </main>
  <p v-else>Fetching {{ endpointUrl }}...</p>
</template>
```

---

## Realtime Composables (`litestar-vite-plugin/vue`)

`litestar-vite-plugin/vue` exports Vue 3 Composition API composables (`useEventStream` and `useQueueEventStream`) returning reactive `Readonly<Ref<...>>` handles that automatically close when the enclosing component unmounts:

```vue title="src/Notifications.vue"
<script setup lang="ts">
import { useEventStream } from "litestar-vite-plugin/vue";

interface NotificationPayload {
  id: string;
  message: string;
}

const { healthy, lastEvent } = useEventStream<NotificationPayload>({
  key: "notifications",
  url: "/api/notifications/stream",
  onEvent: () => {},
});
</script>

<template>
  <aside>
    <span>Stream healthy: {{ healthy }}</span>
    <p v-if="lastEvent">{{ lastEvent.message }}</p>
  </aside>
</template>
```

See [Realtime Event Streams](../typegen/event-streams.md) and [Inertia Overview](inertia/index.md) for server-driven Vue 3 patterns.
