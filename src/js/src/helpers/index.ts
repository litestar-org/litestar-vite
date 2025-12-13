/**
 * Litestar Vite Helpers
 *
 * Utilities for working with Litestar applications from the frontend.
 * These helpers work in both SPA and template modes.
 *
 * @example
 * ```ts
 * import { getCsrfToken, csrfFetch } from 'litestar-vite-plugin/helpers'
 *
 * // Get CSRF token
 * const token = getCsrfToken()
 *
 * // Make a fetch request with CSRF token
 * await csrfFetch('/api/submit', {
 *   method: 'POST',
 *   body: JSON.stringify(data),
 * })
 * ```
 *
 * For type-safe routing, import from your generated routes file:
 * ```ts
 * import { route, routeDefinitions, type RouteName } from '@/generated/routes'
 *
 * // Type-safe URL generation
 * const url = route('user_detail', { user_id: 123 })  // Compile-time checked!
 * ```
 *
 * @module
 */

// CSRF utilities
export { csrfFetch, csrfHeaders, getCsrfToken } from "./csrf.js"
// HTMX utilities
export { addDirective, registerHtmxExtension, setDebug as setHtmxDebug, swapJson } from "./htmx.js"
