---
title: Framework Bindings & Meta-Frameworks
description: TypeScript API reference for React, Vue, Svelte, Astro, SvelteKit, Nuxt, dev-ssr, and ssr-worker subpaths.
---

# Framework Bindings & Meta-Frameworks

Framework-idiomatic reactive stream bindings (`litestar-vite-plugin/react`, `/vue`, `/svelte`), meta-framework Vite/Nitro integrations (`litestar-vite-plugin/astro`, `/sveltekit`, `/nuxt`), and SSR execution transports (`litestar-vite-plugin/dev-ssr`, `/ssr-worker`).

| Subpath | Import Specifier | Source Entrypoint | Exports |
| :--- | :--- | :--- | :--- |
| `./react` | `litestar-vite-plugin/react` | `src/js/src/react/index.ts` | `EventStreamState`, `ReactEventStreamOptions`, `ReactQueueEventStreamOptions`, `AdapterOptions`, `StreamFactory`, `useEventStream`, +1 more |
| `./vue` | `litestar-vite-plugin/vue` | `src/js/src/vue/index.ts` | `VueEventStreamState`, `VueEventStreamOptions`, `VueQueueEventStreamOptions`, `AdapterOptions`, `StreamFactory`, `useEventStream`, +1 more |
| `./svelte` | `litestar-vite-plugin/svelte` | `src/js/src/svelte/index.ts` | `EventStreamStoreState`, `SvelteEventStreamOptions`, `SvelteQueueEventStreamOptions`, `AdapterOptions`, `StreamFactory`, `createEventStreamStore`, +1 more |
| `./astro` | `litestar-vite-plugin/astro` | `src/js/src/astro.ts` | `AstroConfigPartial`, `AddressInfo`, `AstroIntegration`, `AstroIntegrationLogger`, `AstroTypesConfig`, `LitestarAstroConfig`, +1 more |
| `./sveltekit` | `litestar-vite-plugin/sveltekit` | `src/js/src/sveltekit.ts` | `SvelteKitTypesConfig`, `LitestarSvelteKitConfig`, `litestarSvelteKit` |
| `./nuxt` | `litestar-vite-plugin/nuxt` | `src/js/src/nuxt.ts` | `NuxtModuleFunction`, `ListenInfo`, `NuxtContext`, `NuxtTypesConfig`, `LitestarNuxtConfig`, `litestarModule` |
| `./dev-ssr` | `litestar-vite-plugin/dev-ssr` | `src/js/src/dev-ssr.ts` | `litestarViteSsrPlugin` |
| `./ssr-worker` | `litestar-vite-plugin/ssr-worker` | `src/js/src/ssr-worker.ts` | `SsrWorkerOptions`, `IPCRequest`, `dispatchSsrRequest`, `startSsrWorker` |

## `litestar-vite-plugin/react`

**Package Subpath**: `./react` · **Types**: `./dist/js/react/index.d.ts` · **Source**: `src/js/src/react/index.ts`

React bindings for generic and Litestar Queues event streams.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `EventStreamState` | `interface` | Exported `interface` from `src/js/src/react/index.ts`. |
| `ReactEventStreamOptions` | `type` | Exported `type` from `src/js/src/react/index.ts`. |
| `ReactQueueEventStreamOptions` | `type` | Exported `type` from `src/js/src/react/index.ts`. |
| `AdapterOptions` | `type` | Exported `type` from `src/js/src/react/index.ts`. |
| `StreamFactory` | `type` | Exported `type` from `src/js/src/react/index.ts`. |
| `useEventStream` | `function` | Subscribe a React component to a generic event stream. |
| `useQueueEventStream` | `function` | Subscribe a React component to a Litestar Queues event stream. |

#### `EventStreamState`

```ts
export interface EventStreamState<TFrame>
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `healthy` | `boolean` | — | — |
| `lastEvent` | `TFrame \| null` | — | — |
| `lastGap` | `StreamGap \| null` | — | — |
| `events` | `TFrame[]` | — | — |

#### `ReactEventStreamOptions`

```ts
export type ReactEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & {
```

#### `ReactQueueEventStreamOptions`

```ts
export type ReactQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & {
```

#### `AdapterOptions`

```ts
export type AdapterOptions<TFrame> = ReactEventStreamOptions<TFrame> | ReactQueueEventStreamOptions<TFrame>
```

#### `StreamFactory`

```ts
export type StreamFactory = (options: never) => EventStream
```

#### `useEventStream`

```ts
export function useEventStream<TFrame = unknown>(options: ReactEventStreamOptions<TFrame>): EventStreamState<TFrame>
```

Subscribe a React component to a generic event stream.

#### `useQueueEventStream`

```ts
export function useQueueEventStream<TFrame = unknown>(options: ReactQueueEventStreamOptions<TFrame>): EventStreamState<TFrame>
```

Subscribe a React component to a Litestar Queues event stream.

## `litestar-vite-plugin/vue`

**Package Subpath**: `./vue` · **Types**: `./dist/js/vue/index.d.ts` · **Source**: `src/js/src/vue/index.ts`

Vue bindings for generic and Litestar Queues event streams.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `VueEventStreamState` | `interface` | Exported `interface` from `src/js/src/vue/index.ts`. |
| `VueEventStreamOptions` | `type` | Exported `type` from `src/js/src/vue/index.ts`. |
| `VueQueueEventStreamOptions` | `type` | Exported `type` from `src/js/src/vue/index.ts`. |
| `AdapterOptions` | `type` | Exported `type` from `src/js/src/vue/index.ts`. |
| `StreamFactory` | `type` | Exported `type` from `src/js/src/vue/index.ts`. |
| `useEventStream` | `function` | Subscribe a Vue scope to a generic event stream. |
| `useQueueEventStream` | `function` | Subscribe a Vue scope to a Litestar Queues event stream. |

#### `VueEventStreamState`

```ts
export interface VueEventStreamState<TFrame>
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `healthy` | `Ref<boolean>` | — | — |
| `lastEvent` | `ShallowRef<TFrame \| null>` | — | — |
| `lastGap` | `ShallowRef<StreamGap \| null>` | — | — |
| `events` | `ShallowRef<TFrame[]>` | — | — |

#### `VueEventStreamOptions`

```ts
export type VueEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & {
```

#### `VueQueueEventStreamOptions`

```ts
export type VueQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & {
```

#### `AdapterOptions`

```ts
export type AdapterOptions<TFrame> = VueEventStreamOptions<TFrame> | VueQueueEventStreamOptions<TFrame>
```

#### `StreamFactory`

```ts
export type StreamFactory = (options: never) => EventStream
```

#### `useEventStream`

```ts
export function useEventStream<TFrame = unknown>(options: VueEventStreamOptions<TFrame>): VueEventStreamState<TFrame>
```

Subscribe a Vue scope to a generic event stream.

#### `useQueueEventStream`

```ts
export function useQueueEventStream<TFrame = unknown>(options: VueQueueEventStreamOptions<TFrame>): VueEventStreamState<TFrame>
```

Subscribe a Vue scope to a Litestar Queues event stream.

## `litestar-vite-plugin/svelte`

**Package Subpath**: `./svelte` · **Types**: `./dist/js/svelte/index.d.ts` · **Source**: `src/js/src/svelte/index.ts`

Svelte stores for generic and Litestar Queues event streams.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `EventStreamStoreState` | `interface` | Exported `interface` from `src/js/src/svelte/index.ts`. |
| `SvelteEventStreamOptions` | `type` | Exported `type` from `src/js/src/svelte/index.ts`. |
| `SvelteQueueEventStreamOptions` | `type` | Exported `type` from `src/js/src/svelte/index.ts`. |
| `AdapterOptions` | `type` | Exported `type` from `src/js/src/svelte/index.ts`. |
| `StreamFactory` | `type` | Exported `type` from `src/js/src/svelte/index.ts`. |
| `createEventStreamStore` | `function` | Create a readable store backed by a generic event stream. |
| `createQueueEventStreamStore` | `function` | Create a readable store backed by a Litestar Queues event stream. |

#### `EventStreamStoreState`

```ts
export interface EventStreamStoreState<TFrame>
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `healthy` | `boolean` | — | — |
| `lastEvent` | `TFrame \| null` | — | — |
| `lastGap` | `StreamGap \| null` | — | — |
| `events` | `TFrame[]` | — | — |

#### `SvelteEventStreamOptions`

```ts
export type SvelteEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & { bufferSize?: number }
```

#### `SvelteQueueEventStreamOptions`

```ts
export type SvelteQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & { bufferSize?: number }
```

#### `AdapterOptions`

```ts
export type AdapterOptions<TFrame> = SvelteEventStreamOptions<TFrame> | SvelteQueueEventStreamOptions<TFrame>
```

#### `StreamFactory`

```ts
export type StreamFactory = (options: never) => EventStream
```

#### `createEventStreamStore`

```ts
export function createEventStreamStore<TFrame = unknown>(options: SvelteEventStreamOptions<TFrame>): Readable<EventStreamStoreState<TFrame>>
```

Create a readable store backed by a generic event stream.

#### `createQueueEventStreamStore`

```ts
export function createQueueEventStreamStore<TFrame = unknown>(options: SvelteQueueEventStreamOptions<TFrame>): Readable<EventStreamStoreState<TFrame>>
```

Create a readable store backed by a Litestar Queues event stream.

## `litestar-vite-plugin/astro`

**Package Subpath**: `./astro` · **Types**: `./dist/js/astro.d.ts` · **Source**: `src/js/src/astro.ts`

Astro 5 integration for Litestar-Vite.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `AstroConfigPartial` | `interface` | Astro config for updateConfig - partial types we support. |
| `AddressInfo` | `interface` | AddressInfo from Node.js net module. |
| `AstroIntegration` | `interface` | Exported `interface` from `src/js/src/astro.ts`. |
| `AstroIntegrationLogger` | `interface` | Astro integration logger interface. |
| `AstroTypesConfig` | `type` | Configuration for TypeScript type generation. |
| `LitestarAstroConfig` | `type` | Configuration options for the Litestar integration. |
| `litestarAstro` | `default function` | Litestar integration for Astro. |

#### `AstroConfigPartial`

```ts
export interface AstroConfigPartial
```

Astro config for updateConfig - partial types we support.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `server?` | `object` | — | — |
| `vite?` | `object` | — | — |

#### `AddressInfo`

```ts
export interface AddressInfo
```

AddressInfo from Node.js net module.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `address` | `string` | — | — |
| `family` | `string` | — | — |
| `port` | `number` | — | — |

#### `AstroIntegration`

```ts
export interface AstroIntegration
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `string` | — | — |
| `hooks` | `object` | — | — |

#### `AstroIntegrationLogger`

```ts
export interface AstroIntegrationLogger
```

Astro integration logger interface.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `info` | `(message: string) => void` | — | — |
| `warn` | `(message: string) => void` | — | — |
| `error` | `(message: string) => void` | — | — |

#### `AstroTypesConfig`

```ts
export type AstroTypesConfig = TypesConfigShape
```

Configuration for TypeScript type generation.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled?` | `boolean` | — | — |
| `output?` | `string` | — | — |
| `openapiPath?` | `string` | — | — |
| `routesPath?` | `string` | — | — |
| `pagePropsPath?` | `string` | — | — |
| `schemasTsPath?` | `string` | — | — |
| `asyncapiPath?` | `string` | — | — |
| `channelsTsPath?` | `string` | — | — |
| `generateZod?` | `boolean` | — | — |
| `generateSdk?` | `boolean` | — | — |
| `generateRoutes?` | `boolean` | — | — |
| `generatePageProps?` | `boolean` | — | — |
| `generateSchemas?` | `boolean` | — | — |
| `generateChannels?` | `boolean` | — | — |
| `globalRoute?` | `boolean` | — | — |
| `failOnError?` | `boolean` | — | — |
| `debounce?` | `number` | — | — |

#### `LitestarAstroConfig`

```ts
export type LitestarAstroConfig = LitestarIntegrationConfig
```

Configuration options for the Litestar integration.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `apiProxy?` | `string` | — | — |
| `apiPrefix?` | `string` | — | — |
| `types?` | `boolean \| "auto" \| TypesConfigShape` | — | — |
| `verbose?` | `boolean` | — | — |
| `executor?` | `IntegrationExecutor` | — | — |

#### `litestarAstro`

```ts
export default function litestarAstro(userConfig: LitestarAstroConfig =
```

Litestar integration for Astro.

## `litestar-vite-plugin/sveltekit`

**Package Subpath**: `./sveltekit` · **Types**: `./dist/js/sveltekit.d.ts` · **Source**: `src/js/src/sveltekit.ts`

SvelteKit integration for Litestar-Vite.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `SvelteKitTypesConfig` | `type` | Configuration for TypeScript type generation. |
| `LitestarSvelteKitConfig` | `type` | Configuration options for the Litestar integration. |
| `litestarSvelteKit` | `function` | Litestar integration plugin for SvelteKit. |

#### `SvelteKitTypesConfig`

```ts
export type SvelteKitTypesConfig = TypesConfigShape
```

Configuration for TypeScript type generation.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled?` | `boolean` | — | — |
| `output?` | `string` | — | — |
| `openapiPath?` | `string` | — | — |
| `routesPath?` | `string` | — | — |
| `pagePropsPath?` | `string` | — | — |
| `schemasTsPath?` | `string` | — | — |
| `asyncapiPath?` | `string` | — | — |
| `channelsTsPath?` | `string` | — | — |
| `generateZod?` | `boolean` | — | — |
| `generateSdk?` | `boolean` | — | — |
| `generateRoutes?` | `boolean` | — | — |
| `generatePageProps?` | `boolean` | — | — |
| `generateSchemas?` | `boolean` | — | — |
| `generateChannels?` | `boolean` | — | — |
| `globalRoute?` | `boolean` | — | — |
| `failOnError?` | `boolean` | — | — |
| `debounce?` | `number` | — | — |

#### `LitestarSvelteKitConfig`

```ts
export type LitestarSvelteKitConfig = LitestarIntegrationConfig
```

Configuration options for the Litestar integration.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `apiProxy?` | `string` | — | — |
| `apiPrefix?` | `string` | — | — |
| `types?` | `boolean \| "auto" \| TypesConfigShape` | — | — |
| `verbose?` | `boolean` | — | — |
| `executor?` | `IntegrationExecutor` | — | — |

#### `litestarSvelteKit`

```ts
export function litestarSvelteKit(userConfig: LitestarSvelteKitConfig =
```

Litestar integration plugin for SvelteKit.

## `litestar-vite-plugin/nuxt`

**Package Subpath**: `./nuxt` · **Types**: `./dist/js/nuxt.d.ts` · **Source**: `src/js/src/nuxt.ts`

Nuxt 4 module for Litestar-Vite.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `NuxtModuleFunction` | `interface` | Nuxt module definition for Litestar integration. |
| `ListenInfo` | `interface` | Exported `interface` from `src/js/src/nuxt.ts`. |
| `NuxtContext` | `interface` | Exported `interface` from `src/js/src/nuxt.ts`. |
| `NuxtTypesConfig` | `type` | Configuration for TypeScript type generation. |
| `LitestarNuxtConfig` | `type` | Configuration options for the Litestar integration. |
| `litestarModule` | `const` | Exported `const` from `src/js/src/nuxt.ts`. |

#### `NuxtModuleFunction`

```ts
export interface NuxtModuleFunction
```

Nuxt module definition for Litestar integration.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `meta?` | `object` | — | — |
| `getOptions?` | `() => LitestarNuxtConfig` | — | — |

#### `ListenInfo`

```ts
export interface ListenInfo
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `url?` | `string` | — | — |
| `address?` | `object` | — | — |
| `host?` | `string` | — | — |
| `port?` | `number` | — | — |

#### `NuxtContext`

```ts
export interface NuxtContext
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `options` | `object` | — | — |
| `hook?` | `(name: string, fn: (...args: unknown[]) => void \| Promise<void>) => void` | — | — |

#### `NuxtTypesConfig`

```ts
export type NuxtTypesConfig = TypesConfigShape
```

Configuration for TypeScript type generation.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled?` | `boolean` | — | — |
| `output?` | `string` | — | — |
| `openapiPath?` | `string` | — | — |
| `routesPath?` | `string` | — | — |
| `pagePropsPath?` | `string` | — | — |
| `schemasTsPath?` | `string` | — | — |
| `asyncapiPath?` | `string` | — | — |
| `channelsTsPath?` | `string` | — | — |
| `generateZod?` | `boolean` | — | — |
| `generateSdk?` | `boolean` | — | — |
| `generateRoutes?` | `boolean` | — | — |
| `generatePageProps?` | `boolean` | — | — |
| `generateSchemas?` | `boolean` | — | — |
| `generateChannels?` | `boolean` | — | — |
| `globalRoute?` | `boolean` | — | — |
| `failOnError?` | `boolean` | — | — |
| `debounce?` | `number` | — | — |

#### `LitestarNuxtConfig`

```ts
export type LitestarNuxtConfig = LitestarIntegrationConfig
```

Configuration options for the Litestar integration.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `apiProxy?` | `string` | — | — |
| `apiPrefix?` | `string` | — | — |
| `types?` | `boolean \| "auto" \| TypesConfigShape` | — | — |
| `verbose?` | `boolean` | — | — |
| `executor?` | `IntegrationExecutor` | — | — |

#### `litestarModule`

```ts
export const litestarModule: NuxtModuleFunction
```

## `litestar-vite-plugin/dev-ssr`

**Package Subpath**: `./dev-ssr` · **Types**: `./dist/js/dev-ssr.d.ts` · **Source**: `src/js/src/dev-ssr.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `litestarViteSsrPlugin` | `function` | Exported `function` from `src/js/src/dev-ssr.ts`. |

#### `litestarViteSsrPlugin`

```ts
export function litestarViteSsrPlugin(options: DevSsrOptions =
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
| `render?` | `(page: any) => unknown \| Promise<unknown>` | — | — |
| `renderFragment?` | `(params: Record<string, unknown>) => unknown \| Promise<unknown>` | — | — |

#### `IPCRequest`

```ts
export interface IPCRequest
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id?` | `number \| string` | — | — |
| `method?` | `string` | — | — |
| `params?` | `Record<string, unknown>` | — | — |
| `payload?` | `Record<string, unknown>` | — | — |

#### `dispatchSsrRequest`

```ts
export async function dispatchSsrRequest(request: IPCRequest, options: SsrWorkerOptions =
```

Dispatch one request, preserving rendering errors for the transport's fallback policy.

#### `startSsrWorker`

```ts
export function startSsrWorker(options: SsrWorkerOptions =
```

Start the shared newline-delimited JSON RPC worker for an application's SSR entry.
