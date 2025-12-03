/**
 * Litestar Vite Helpers
 *
 * Utilities for working with Litestar applications from the frontend.
 * These helpers work in both SPA and template modes.
 *
 * @example
 * ```ts
 * import { route, getCsrfToken, csrfFetch } from 'litestar-vite-plugin/helpers'
 *
 * // Generate a URL for a named route
 * const url = route('user:detail', { user_id: 123 })
 *
 * // Make a fetch request with CSRF token
 * await csrfFetch('/api/submit', {
 *   method: 'POST',
 *   body: JSON.stringify(data),
 * })
 * ```
 *
 * @module
 */

// CSRF utilities
export { csrfFetch, csrfHeaders, getCsrfToken } from "./csrf.js"
// HTMX utilities
export { addDirective, registerHtmxExtension, setDebug as setHtmxDebug, swapJson } from "./htmx.js"
// Route utilities
export {
  currentRoute,
  getRelativeUrlPath,
  getRoutes,
  isCurrentRoute,
  isRoute,
  LITESTAR,
  type LitestarHelpers,
  type RouteDefinition,
  type RoutesMap,
  route,
  toRoute,
} from "./routes.js"
