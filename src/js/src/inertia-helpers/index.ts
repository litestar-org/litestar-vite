/**
 * Inertia.js helpers for Litestar applications.
 *
 * This module re-exports common helpers from litestar-vite-plugin/helpers
 * and adds Inertia-specific utilities.
 *
 * For type-safe routing, import from your generated routes file:
 * ```ts
 * import { route, routes, type RouteName } from '@/generated/routes'
 * ```
 *
 * @module
 */

// Re-export all helpers from the main helpers module
// Note: Using package path instead of relative import to ensure proper build output structure
export {
  csrfFetch,
  csrfHeaders,
  // CSRF utilities
  getCsrfToken,
} from "litestar-vite-plugin/helpers"

/**
 * Unwrap page props that may have content nested under "content" key.
 *
 * Litestar wraps route return values under `content`. This utility
 * spreads the content at the top level for ergonomic prop access.
 *
 * @param props - The raw page props from Inertia
 * @returns Props with content unwrapped if applicable
 */
export function unwrapPageProps<T extends Record<string, unknown>>(props: T): T {
  if (props.content !== undefined && props.content !== null && typeof props.content === "object" && !Array.isArray(props.content)) {
    const { content, ...rest } = props
    return { ...rest, ...(content as Record<string, unknown>) } as T
  }
  return props
}

/**
 * Wrap a component to automatically unwrap Litestar's content prop.
 *
 * @param component - The original component (function or object with default)
 * @returns Wrapped component that transforms props
 */
function wrapComponent<T>(module: T): T {
  // Handle ES module with default export
  const mod = module as Record<string, unknown>
  if (mod.default && typeof mod.default === "function") {
    const Original = mod.default as (props: Record<string, unknown>) => unknown
    const Wrapped = (props: Record<string, unknown>) => Original(unwrapPageProps(props))
    // Copy static properties (displayName, layout, etc.)
    Object.assign(Wrapped, Original)
    return { ...mod, default: Wrapped } as T
  }
  // Handle direct function export
  if (typeof module === "function") {
    const Original = module as unknown as (props: Record<string, unknown>) => unknown
    const Wrapped = (props: Record<string, unknown>) => Original(unwrapPageProps(props))
    Object.assign(Wrapped, Original)
    return Wrapped as T
  }
  return module
}

/**
 * Resolve a page component from a glob import.
 *
 * Used with Inertia.js to dynamically import page components.
 * Automatically unwraps Litestar's `content` prop for ergonomic access.
 *
 * @param path - Component path or array of paths to try
 * @param pages - Glob import result (e.g., import.meta.glob('./pages/**\/*.vue'))
 * @returns Promise resolving to the component
 * @throws Error if no matching component is found
 *
 * @example
 * ```ts
 * import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers'
 *
 * createInertiaApp({
 *   resolve: (name) => resolvePageComponent(
 *     `./pages/${name}.vue`,
 *     import.meta.glob('./pages/**\/*.vue')
 *   ),
 *   // ...
 * })
 * ```
 */
export async function resolvePageComponent<T>(path: string | string[], pages: Record<string, Promise<T> | (() => Promise<T>)>): Promise<T> {
  for (const p of Array.isArray(path) ? path : [path]) {
    const page = pages[p]

    if (typeof page === "undefined") {
      continue
    }

    const resolved = typeof page === "function" ? await page() : await page
    return wrapComponent(resolved)
  }

  throw new Error(`Page not found: ${path}`)
}
