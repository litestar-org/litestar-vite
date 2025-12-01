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
export { getCsrfToken, csrfHeaders, csrfFetch } from "./csrf.js"

// Route utilities
export {
  route,
  getRoutes,
  toRoute,
  currentRoute,
  isRoute,
  isCurrentRoute,
  getRelativeUrlPath,
  LITESTAR,
  type RouteDefinition,
  type RoutesMap,
  type LitestarHelpers,
} from "./routes.js"
