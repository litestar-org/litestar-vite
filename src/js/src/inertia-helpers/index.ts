/**
 * Inertia.js helpers for Litestar applications.
 *
 * This module re-exports common helpers from litestar-vite-plugin/helpers
 * and adds Inertia-specific utilities.
 *
 * @module
 */

// Re-export all helpers from the main helpers module
export {
  // CSRF utilities
  getCsrfToken,
  csrfHeaders,
  csrfFetch,
  // Route utilities
  route,
  getRoutes,
  toRoute,
  currentRoute,
  isRoute,
  isCurrentRoute,
  getRelativeUrlPath,
  type RouteDefinition,
  type RoutesMap,
} from "../helpers/index.js"

/**
 * Resolve a page component from a glob import.
 *
 * Used with Inertia.js to dynamically import page components.
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

    return typeof page === "function" ? page() : page
  }

  throw new Error(`Page not found: ${path}`)
}
