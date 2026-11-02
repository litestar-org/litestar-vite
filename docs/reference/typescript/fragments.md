---
title: Server Fragments, Islands & SSR Runtimes
description: TypeScript API reference for litestar-vite-plugin/fragments, client hydration adapters, dev-ssr, and ssr-worker.
---

# Server Fragments, Islands & SSR Runtimes

Server-rendered component fragments (`litestar-vite-plugin/fragments`), `<litestar-island>` progressive hydration adapters (`litestar-vite-plugin/fragments/client`, `/react`, `/vue`, `/svelte`), and SSR execution transports (`litestar-vite-plugin/dev-ssr`, `/ssr-worker`).

| Subpath | Import Specifier | Source Entrypoint | Exports |
| :--- | :--- | :--- | :--- |
| `./fragments` | `litestar-vite-plugin/fragments` | `src/js/src/fragments/renderer.ts` | `RenderFragmentOptions`, `RenderFragmentResult`, `renderFragment`, `createFragmentRenderer` |
| `./fragments/client` | `litestar-vite-plugin/fragments/client` | `src/js/src/fragments/client.ts` | `IslandComponent`, `IslandTeardown`, `IslandHydrator`, `hydrateIslands` |
| `./fragments/react` | `litestar-vite-plugin/fragments/react` | `src/js/src/fragments/react.ts` | `hydrateReact` |
| `./fragments/vue` | `litestar-vite-plugin/fragments/vue` | `src/js/src/fragments/vue.ts` | `hydrateVue` |
| `./fragments/svelte` | `litestar-vite-plugin/fragments/svelte` | `src/js/src/fragments/svelte.ts` | `hydrateSvelte` |
| `./dev-ssr` | `litestar-vite-plugin/dev-ssr` | `src/js/src/dev-ssr.ts` | `litestarViteSsrPlugin` |
| `./ssr-worker` | `litestar-vite-plugin/ssr-worker` | `src/js/src/ssr-worker.ts` | `SsrWorkerOptions`, `IPCRequest`, `dispatchSsrRequest`, `startSsrWorker` |

## `litestar-vite-plugin/fragments`

**Package Subpath**: `./fragments` · **Types**: `./dist/js/fragments/renderer.d.ts` · **Source**: `src/js/src/fragments/renderer.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `RenderFragmentOptions` | `interface` | Exported `interface` from `src/js/src/fragments/renderer.ts`. |
| `RenderFragmentResult` | `interface` | Exported `interface` from `src/js/src/fragments/renderer.ts`. |
| `renderFragment` | `function` | Exported `function` from `src/js/src/fragments/renderer.ts`. |
| `createFragmentRenderer` | `function` | Create a production renderer from imports compiled by the application's SSR build. |

#### `RenderFragmentOptions`

```ts
export interface RenderFragmentOptions
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `componentPath` | `string` | — | — |
| `props?` | `Record<string, unknown>` | — | — |
| `mode?` | <code>"static" &#124; "island"</code> | — | — |
| `islandId?` | `string` | — | — |
| `clientEntry?` | `string` | — | — |

#### `RenderFragmentResult`

```ts
export interface RenderFragmentResult
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `html` | `string` | — | — |
| `head` | `string[]` | — | — |
| `css` | `string[]` | — | — |

#### `renderFragment`

```ts
export async function renderFragment(options: RenderFragmentOptions, customImporter?: (specifier: string) => Promise<any>): Promise<RenderFragmentResult>
```

#### `createFragmentRenderer`

```ts
export function createFragmentRenderer( registry: Record<string, () => Promise<any>>, options: { clientEntry?: string } = {}, ): (params: Record<string, unknown>) => Promise<RenderFragmentResult>
```

Create a production renderer from imports compiled by the application's SSR build.

## `litestar-vite-plugin/fragments/client`

**Package Subpath**: `./fragments/client` · **Types**: `./dist/js/fragments/client.d.ts` · **Source**: `src/js/src/fragments/client.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `IslandComponent` | `interface` | Exported `interface` from `src/js/src/fragments/client.ts`. |
| `IslandTeardown` | `type` | Exported `type` from `src/js/src/fragments/client.ts`. |
| `IslandHydrator` | `type` | Exported `type` from `src/js/src/fragments/client.ts`. |
| `hydrateIslands` | `function` | Register compiled component imports and hydrate present and subsequently inserted islands. |

#### `IslandComponent`

```ts
export interface IslandComponent
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `load` | `() => Promise<{ default: any }>` | — | — |
| `hydrate` | `IslandHydrator` | — | — |

#### `IslandTeardown`

```ts
export type IslandTeardown = () => void | Promise<void>
```

#### `IslandHydrator`

```ts
export type IslandHydrator = (component: any, target: HTMLElement, props: Record<string, unknown>) => IslandTeardown | Promise<IslandTeardown>
```

#### `hydrateIslands`

```ts
export function hydrateIslands(registry: Record<string, IslandComponent>): void
```

Register compiled component imports and hydrate present and subsequently inserted islands.

## `litestar-vite-plugin/fragments/react`

**Package Subpath**: `./fragments/react` · **Types**: `./dist/js/fragments/react.d.ts` · **Source**: `src/js/src/fragments/react.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `hydrateReact` | `const` | Exported `const` from `src/js/src/fragments/react.ts`. |

#### `hydrateReact`

```ts
export const hydrateReact: IslandHydrator
```

## `litestar-vite-plugin/fragments/vue`

**Package Subpath**: `./fragments/vue` · **Types**: `./dist/js/fragments/vue.d.ts` · **Source**: `src/js/src/fragments/vue.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `hydrateVue` | `const` | Exported `const` from `src/js/src/fragments/vue.ts`. |

#### `hydrateVue`

```ts
export const hydrateVue: IslandHydrator
```

## `litestar-vite-plugin/fragments/svelte`

**Package Subpath**: `./fragments/svelte` · **Types**: `./dist/js/fragments/svelte.d.ts` · **Source**: `src/js/src/fragments/svelte.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `hydrateSvelte` | `const` | Exported `const` from `src/js/src/fragments/svelte.ts`. |

#### `hydrateSvelte`

```ts
export const hydrateSvelte: IslandHydrator
```

## `litestar-vite-plugin/dev-ssr`

**Package Subpath**: `./dev-ssr` · **Types**: `./dist/js/dev-ssr.d.ts` · **Source**: `src/js/src/dev-ssr.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `litestarViteSsrPlugin` | `function` | Exported `function` from `src/js/src/dev-ssr.ts`. |

#### `litestarViteSsrPlugin`

```ts
export function litestarViteSsrPlugin(options: DevSsrOptions = {}): Plugin
```

## `litestar-vite-plugin/ssr-worker`

**Package Subpath**: `./ssr-worker` · **Types**: `./dist/js/ssr-worker.d.ts` · **Source**: `src/js/src/ssr-worker.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `SsrWorkerOptions` | `interface` | Exported `interface` from `src/js/src/ssr-worker.ts`. |
| `IPCRequest` | `interface` | Exported `interface` from `src/js/src/ssr-worker.ts`. |
| `dispatchSsrRequest` | `function` | Dispatch one request, preserving rendering errors for the transport's fallback policy. |
| `startSsrWorker` | `function` | Start the shared newline-delimited JSON RPC worker for an application's SSR entry. |

#### `SsrWorkerOptions`

```ts
export interface SsrWorkerOptions
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `render?` | <code>(page: any) =&gt; unknown &#124; Promise&lt;unknown&gt;</code> | — | — |
| `renderFragment?` | <code>(params: Record&lt;string, unknown&gt;) =&gt; unknown &#124; Promise&lt;unknown&gt;</code> | — | — |

#### `IPCRequest`

```ts
export interface IPCRequest
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id?` | <code>number &#124; string</code> | — | — |
| `method?` | `string` | — | — |
| `params?` | `Record<string, unknown>` | — | — |
| `payload?` | `Record<string, unknown>` | — | — |

#### `dispatchSsrRequest`

```ts
export async function dispatchSsrRequest(request: IPCRequest, options: SsrWorkerOptions = {}): Promise<unknown>
```

Dispatch one request, preserving rendering errors for the transport's fallback policy.

#### `startSsrWorker`

```ts
export function startSsrWorker(options: SsrWorkerOptions = {}): void
```

Start the shared newline-delimited JSON RPC worker for an application's SSR entry.
