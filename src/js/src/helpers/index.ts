/**
 * Litestar Vite Helpers
 *
 * Utilities for working with Litestar applications from the frontend.
 * These helpers work in both SPA and template modes.
 *
 * @example
 * ```ts
 * // CSRF utilities
 * import { getCsrfToken, csrfFetch } from 'litestar-vite-plugin/helpers'
 *
 * const token = getCsrfToken()
 * await csrfFetch('/api/submit', { method: 'POST', body: JSON.stringify(data) })
 * ```
 *
 * @example
 * ```ts
 * // Route matching utilities
 * import { createRouteHelpers } from 'litestar-vite-plugin/helpers'
 * import { routeDefinitions } from '@/generated/routes'
 *
 * const { isCurrentRoute, currentRoute, toRoute, isRoute } = createRouteHelpers(routeDefinitions)
 *
 * // Highlight active nav items
 * if (isCurrentRoute('dashboard')) { ... }
 *
 * // Match with wildcards
 * if (isCurrentRoute('book_*')) { ... }
 * ```
 *
 * @example
 * ```ts
 * // Type-safe URL generation (from generated routes)
 * import { route } from '@/generated/routes'
 *
 * const url = route('user_detail', { user_id: 123 })  // Compile-time checked!
 * ```
 *
 * @module
 */

// CSRF utilities
export { csrfFetch, csrfHeaders, getCsrfHeaderName, getCsrfToken } from "./csrf.js"
// Litestar Channels utilities
export { createChannelsStream, type ChannelName, type ChannelsStreamOptions } from "./channels.js"
// HTMX utilities
export { addDirective, registerHtmxExtension, setDebug as setHtmxDebug, swapJson } from "./htmx.js"
// Litestar Queues utilities
export { createQueueEventStream, QUEUE_SSE_EVENTS, type QueueEventStreamOptions, type QueueStreamTarget, type QueueStreamValue } from "./queues.js"
// Route matching utilities
export { createRouteHelpers, currentRoute, isCurrentRoute, isRoute, type RouteDefinition, type RouteDefinitions, type RouteHelpers, toRoute } from "./routes.js"
// Realtime stream utilities
export { createEventStream, type EventStream, type EventStreamOptions, type StreamGap } from "./stream.js"
// Declarative realtime stream element
export { defineStreamElement, LitestarStreamElement, type StreamElementOptions } from "./stream-element.js"
