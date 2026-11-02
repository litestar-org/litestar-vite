# React, Vue 3 & Svelte 5 Setup

Whether you run in `mode="spa"`, `mode="hybrid"` (Inertia v2), or `mode="template"` (Jinja2 + Islands), `litestar-vite-plugin` integrates directly with the official Vite 7+ plugins for React, Vue 3, and Svelte 5.

---

## 1. Vite Configuration (`vite.config.ts`)

=== "React 19"

    ```typescript title="vite.config.ts"
    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        react(),
        litestar({
          input: ["src/main.tsx"],
        }),
      ],
    });
    ```

=== "Vue 3"

    ```typescript title="vite.config.ts"
    import { defineConfig } from "vite";
    import vue from "@vitejs/plugin-vue";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        vue(),
        litestar({
          input: ["src/main.ts"],
        }),
      ],
    });
    ```

=== "Svelte 5"

    ```typescript title="vite.config.ts"
    import { defineConfig } from "vite";
    import { svelte } from "@sveltejs/vite-plugin-svelte";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        svelte(),
        litestar({
          input: ["src/main.ts"],
        }),
      ],
    });
    ```

---

## 2. React Fast Refresh Preamble (`RuntimeConfig.is_react`)

Unlike Vue and Svelte, `@vitejs/plugin-react` requires an inline `<script type="module">` Fast Refresh preamble (`/@react-refresh`) in `<head>` before any `.tsx` or `.jsx` module is imported in development:

- **Auto-Detection**: When `litestar-vite-plugin` detects `@vitejs/plugin-react` (or `@vitejs/plugin-react-swc`) in `vite.config.ts`, or when `RuntimeConfig(is_react=True)` is set in Python, `ViteAssetLoader.render_hmr_client()` automatically injects the React Fast Refresh preamble alongside `/@vite/client`.
- **Zero Production Overhead**: In production (`dev_mode=False`), `render_hmr_client()` returns an empty string `""`.

---

## 3. Framework Realtime & SSE Composables

`litestar-vite-plugin` ships framework-native reactive hooks for Server-Sent Events (`EventSource`) and AsyncAPI WebSocket channels under dedicated subpaths:

| Framework | Import Subpath | Exports |
| --- | --- | --- |
| **React** | `litestar-vite-plugin/react` | `useEventStream`, `useWsChannel` |
| **Vue 3** | `litestar-vite-plugin/vue` | `useEventStream`, `useWsChannel` |
| **Svelte 5** | `litestar-vite-plugin/svelte` | `createEventStreamStore`, `createWsChannelStore` |

See [AsyncAPI & Realtime Channels](../typegen/realtime-channels.md) for end-to-end typed usage with `channels.ts`.
