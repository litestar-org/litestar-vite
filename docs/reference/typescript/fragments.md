---
title: Server Fragments & Islands
description: TypeScript API reference for litestar-vite-plugin/fragments and client hydration adapters.
---

# Server Fragments & Islands

Server-rendered component fragments (`litestar-vite-plugin/fragments`) and `<litestar-island>` progressive hydration adapters (`litestar-vite-plugin/fragments/client`, `/react`, `/vue`, `/svelte`).

| Subpath | Import Specifier | Source Entrypoint | Exports |
| :--- | :--- | :--- | :--- |
| `./fragments` | `litestar-vite-plugin/fragments` | `src/js/src/fragments/renderer.ts` | `RenderFragmentOptions`, `RenderFragmentResult`, `renderFragment`, `createFragmentRenderer` |
| `./fragments/client` | `litestar-vite-plugin/fragments/client` | `src/js/src/fragments/client.ts` | `IslandComponent`, `IslandTeardown`, `IslandHydrator`, `hydrateIslands` |
| `./fragments/react` | `litestar-vite-plugin/fragments/react` | `src/js/src/fragments/react.ts` | `hydrateReact` |
| `./fragments/vue` | `litestar-vite-plugin/fragments/vue` | `src/js/src/fragments/vue.ts` | `hydrateVue` |
| `./fragments/svelte` | `litestar-vite-plugin/fragments/svelte` | `src/js/src/fragments/svelte.ts` | `hydrateSvelte` |

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
| `mode?` | `"static" \| "island"` | — | — |
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
export function createFragmentRenderer( registry: Record<string, () => Promise<any>>, options:
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
