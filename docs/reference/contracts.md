---
title: Bridge & IPC Wire Contracts
description: Wire-level specifications for .litestar.json, routes.json, openapi.json, asyncapi.json, virtual:litestar-static-props, and SSR/Fragment IPC envelopes.
---

# Bridge & IPC Wire Contracts

Litestar Vite coordinates the Python ASGI process and the JavaScript Vite / SSR runtime through deterministic JSON files and newline-delimited JSON (NDJSON) / HTTP IPC envelopes. Every contract is validated strictly on both sides.

---

## `.litestar.json` Bridge Configuration

On application startup (and before CLI asset commands), `VitePlugin` writes `.litestar.json` to the project root (or `LITESTAR_VITE_CONFIG_PATH`). The `litestar-vite-plugin` Vite plugin and the Astro, SvelteKit, and Nuxt integrations read this file via `readBridgeConfig()` (`BridgeSchema`) so paths, ports, and typegen flags never have to be duplicated across `app.py` and `vite.config.ts`.

### Schema

```json
{
  "assetUrl": "/static/",
  "deployAssetUrl": null,
  "appUrl": "http://127.0.0.1:8000",
  "csrfCookieName": "csrftoken",
  "csrfHeaderName": "x-csrftoken",
  "litestarPort": 8000,
  "bundleDir": "public",
  "resourceDir": "src",
  "staticDir": "src/public",
  "hotFile": "hot",
  "manifest": "manifest.json",
  "mode": "spa",
  "proxyMode": "vite",
  "host": "127.0.0.1",
  "port": 5173,
  "ssrOutDir": null,
  "executor": "node",
  "litestarVersion": "2.16.0",
  "logging": {
    "level": "normal",
    "showPathsAbsolute": false,
    "suppressNpmOutput": false,
    "suppressViteBanner": false,
    "timestamps": false
  },
  "spa": {
    "useScriptElement": false
  },
  "types": {
    "enabled": true,
    "output": "src/generated",
    "openapiPath": "src/generated/openapi.json",
    "routesPath": "src/generated/routes.json",
    "pagePropsPath": "src/generated/inertia-pages.json",
    "routesTsPath": "src/generated/routes.ts",
    "schemasTsPath": "src/generated/schemas.ts",
    "asyncapiPath": "src/generated/asyncapi.json",
    "channelsTsPath": "src/generated/channels.ts",
    "generateZod": false,
    "generateSdk": true,
    "generateRoutes": true,
    "generatePageProps": true,
    "generateSchemas": true,
    "generateChannels": true,
    "globalRoute": false,
    "failOnError": true
  },
  "staticProps": {
    "appName": "Bookstore",
    "environment": "development"
  }
}
```

### Top-Level Fields

| Field | Type | Source in Python | Description |
| :--- | :--- | :--- | :--- |
| `assetUrl` | `string` | `PathConfig.asset_url` | Base URL prefix for static assets (e.g. `"/static/"`). |
| `deployAssetUrl` | <code>string &#124; null</code> | `DeployConfig.asset_url` | Optional CDN/storage asset URL override applied only during `vite build`. |
| `appUrl` | <code>string &#124; null</code> | `RuntimeConfig.app_url` | Canonical Litestar server URL discovered at startup. |
| `csrfCookieName` | <code>string &#124; null</code> | `Litestar.csrf_config` | Configured CSRF cookie name when CSRF protection is active. |
| `csrfHeaderName` | <code>string &#124; null</code> | `Litestar.csrf_config` | Configured CSRF request header name when CSRF protection is active. |
| `litestarPort` | <code>number &#124; null</code> | `RuntimeConfig` | Port where the Litestar server is listening; used for single-port HMR WebSocket routing. |
| `bundleDir` | `string` | `PathConfig.bundle_dir` | Directory where compiled production bundles and the manifest are written. |
| `resourceDir` | `string` | `PathConfig.resource_dir` | Frontend source directory (aliased to `@/` in Vite). |
| `staticDir` | `string` | `PathConfig.static_dir` | Unprocessed static assets directory (mapped to Vite's `publicDir`). |
| `hotFile` | `string` | `PathConfig.hot_file` | Relative file name inside `bundleDir` where the running Vite server writes its origin URL. |
| `manifest` | `string` | `PathConfig.manifest_name` | Vite asset manifest filename inside `bundleDir`. |
| `mode` | <code>"spa" &#124; "template" &#124; "hybrid" &#124; "framework" &#124; "external"</code> | `ViteConfig.mode` | Resolved operating mode. |
| `proxyMode` | <code>"vite" &#124; "direct" &#124; "proxy" &#124; null</code> | `RuntimeConfig.proxy_mode` | Active development proxy strategy (`null` when disabled). |
| `host` | `string` | `RuntimeConfig.host` | Vite dev server bind address (`"127.0.0.1"` by default). |
| `port` | `number` | `RuntimeConfig.port` | Vite dev server port (`5173` by default). |
| `ssrOutDir` | <code>string &#124; null</code> | `PathConfig.ssr_output_dir` | Output directory for compiled SSR bundles. |
| `executor` | <code>"node" &#124; "bun" &#124; "deno" &#124; "yarn" &#124; "pnpm"</code> | `RuntimeConfig.executor` | JavaScript package/runtime executor. |
| `litestarVersion` | `string` | `litestar.__version__` | Installed Litestar package version string. |
| `logging` | <code>object &#124; null</code> | `LoggingConfig` | Console logging preferences shared with the Vite plugin. |
| `spa` | <code>object &#124; null</code> | `InertiaConfig` / `SPAConfig` | SPA and Inertia HTML transform settings (`useScriptElement`). |
| `types` | <code>BridgeTypesConfig &#124; null</code> | `TypeGenConfig` | Type generation paths and feature flags (`null` when `types=False`). |
| `staticProps` | <code>Record&lt;string, unknown&gt; &#124; null</code> | `ViteConfig.static_props` | Static key-value payload exposed via `virtual:litestar-static-props`. |

---

## `routes.json` & Type-Gen Metadata Files

When `TypeGenConfig` is enabled (`ViteConfig(types=True)` or `ViteConfig(types=TypeGenConfig(...))`), Python exports deterministic JSON artifacts to `TypeGenConfig.output` (only rewriting files on disk when byte content changes):

### `routes.json`

Contains all registered HTTP and WebSocket routes (filtered by `exclude_routes`), parameter types, and OpenAPI `operationId` or AsyncAPI `channel_key` links. Used by both Python and the Vite plugin to emit `routes.ts` (`route()`, `toRoute()`, `wsRoute()`, `routeDefinitions`) and `schemas.ts` (`FormInput`, `FormResponse`, `SuccessResponse`).

```json
{
  "servers": "ws://127.0.0.1:8000",
  "routes": {
    "books:list": {
      "uri": "/api/books",
      "methods": ["GET"],
      "method": "get",
      "parameters": {},
      "queryParameters": {
        "q": { "type": "string", "required": false, "default": null }
      },
      "operationId": "list_books_api_books_get"
    },
    "ws_notifications": {
      "uri": "/ws/notifications",
      "methods": [],
      "protocol": "websocket",
      "parameters": {},
      "queryParameters": {},
      "channel_key": "ws__notifications"
    }
  }
}
```

### `openapi.json`

Canonical OpenAPI 3.1 schema exported from Litestar with deterministic key ordering. Consumed by `@hey-api/openapi-ts` to generate `api/types.gen.ts` and the typed SDK client.

### `inertia-pages.json`

Maps Inertia component names (`component="..."` on route handlers) to their return-type TypeScript schemas or OpenAPI `$ref` names, alongside shared props registered on `InertiaConfig`. Consumed by the Vite plugin to generate `page-props.ts`.

### `asyncapi.json`

AsyncAPI 3.0 document exported from `ChannelsPlugin` and WebSocket route handlers (`generate_asyncapi_schema()`). Consumed by the Vite plugin (`@asyncapi/parser`) to emit `channels.ts` (`ChannelMap`, `ChannelName`, `ChannelPayload`, `bindTypedChannels()`).

---

## `virtual:litestar-static-props`

The `litestar-vite-plugin` registers a Rollup/Vite virtual module `virtual:litestar-static-props` (resolved internally as `\0virtual:litestar-static-props`) that serializes `BridgeSchema.staticProps` into an ES module with both a default export and named top-level exports for every valid JavaScript identifier key.

```ts
/// <reference types="litestar-vite-plugin/virtual" />
import staticProps, { appName } from "virtual:litestar-static-props"
```

Ambient declarations live in `litestar-vite-plugin/virtual` (`StaticProps` interface), and when `TypeGenConfig` is enabled, `static-props.d.ts` augments `StaticProps` with exact TypeScript types inferred from `ViteConfig.static_props`.

---

## SSR & Fragment IPC Protocol

Server-side rendering (`InertiaPlugin` SSR and `FragmentEngine.render()`) uses a unified JSON-RPC-like request/response envelope (`IPCRequest` and `IPCResponse` in Python; `SsrRenderResponse` in TypeScript) across both development and production transports:

- **Development (`TCPStreamIPCTransport`)**: Sends `POST /__litestar_ssr__` over `anyio.connect_tcp` to Vite's `litestarViteSsrPlugin` (`litestar-vite-plugin/dev-ssr`), which executes modules through Vite 7+'s `ServerModuleRunner`. Browser requests (containing `Origin` or `Sec-Fetch-Site` headers) are rejected with 403 Forbidden.
- **Production (`StdioIPCTransport`)**: Spawns a long-lived worker (`startSsrWorker` from `litestar-vite-plugin/ssr-worker`) and exchanges newline-delimited JSON (NDJSON) lines over `stdin`/`stdout` while draining `stderr` concurrently.
- **Production In-Process (`WasmIPCTransport`)**: Evaluates the self-contained ES-module `ssr.js` bundle inside an embedded QuickJS engine (`litestar-vite[wasm]`) on a dedicated worker thread via `globalThis.__litestar_ssr_dispatch__`.

### Request Envelope

```ts
export interface IPCRequest {
  id?: number | string
  method?: "render" | "render_fragment" | "ping"
  params?: Record<string, unknown>
  payload?: Record<string, unknown>
}
```

#### Inertia Page Render

```json
{
  "id": "req-1",
  "method": "render",
  "params": {
    "page": {
      "component": "Books/Index",
      "props": { "books": [] },
      "url": "/books",
      "version": "1.0"
    }
  }
}
```

#### Server Fragment / Island Render

```json
{
  "id": "req-2",
  "method": "render_fragment",
  "params": {
    "component": "components/Chart.tsx",
    "props": { "series": [10, 20, 30] },
    "mode": "island"
  }
}
```

### Response Envelope

```ts
export interface SsrRenderResponse {
  id?: number | string
  result?: {
    head?: string[]
    body?: string
    html?: string
    css?: string[]
  }
  error?: {
    message: string
    stack?: string
    name?: string
  }
}
```

- **Success (`method: "render"`)**: `result` contains `head: string[]` and `body: string`.
- **Success (`method: "render_fragment"`)**: `result` contains `html: string`, `head: string[]`, and `css: string[]`. When `mode === "island"`, `html` wraps the server-rendered markup in `<litestar-island data-island-id="..." data-island-component="..." data-island-props="...">` and appends a one-time module script loader for `clientEntry`.
- **Failure**: `error` contains `message` (and optional Vite SSR stack-fixed `stack` and `name`). In Python, `SSRCircuitBreaker` records the failure and falls back to client-side rendering when `fallback_to_client=True`.
