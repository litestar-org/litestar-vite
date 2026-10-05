/**
 * Route matching utilities for Litestar applications.
 *
 * These helpers work with the generated `routeDefinitions` from your routes.ts file
 * to provide runtime route matching capabilities.
 *
 * **IMPORTANT**: This file serves as both the runtime library AND the reference
 * implementation for the Python code generator. The same logic is also generated
 * inline in `routes.ts` by `src/py/litestar_vite/_codegen/routes.py`.
 *
 * **If you modify the logic here, you MUST also update the Python generator!**
 *
 * @example
 * ```ts
 * import { routeDefinitions } from '@/generated/routes'
 * import { createRouteHelpers } from 'litestar-vite-plugin/helpers'
 *
 * const { isCurrentRoute, currentRoute, toRoute, isRoute } = createRouteHelpers(routeDefinitions)
 *
 * // Check if current URL matches a route
 * if (isCurrentRoute('dashboard')) {
 *   // highlight nav item
 * }
 * ```
 *
 * @module
 */

/**
 * Route definition structure from generated routes.
 */
export interface RouteDefinition {
  path: string
  methods: readonly string[]
  method?: string
  pathParams: readonly string[]
  queryParams: readonly string[]
  component?: string
  protocol?: "http" | "websocket"
  channelKey?: string
}

/**
 * Map of route names to their definitions.
 */
export type RouteDefinitions = Record<string, RouteDefinition>

/**
 * Options for resolving WebSocket route URLs.
 */
export interface WsRouteOptions {
  /** Explicit server or base URL (e.g. from AsyncAPI servers or VITE_API_URL). */
  serverUrl?: string
  /** Explicit WebSocket server URL override for `route.ws()` / `wsRoute()`. */
  wsServerUrl?: string
}

/**
 * Extract route names from a RouteDefinitions map that declare `protocol: "websocket"`.
 */
export type WebSocketRouteNames<TRoutes extends Record<string, RouteDefinition>> = {
  [K in keyof TRoutes & string]: TRoutes[K] extends { protocol: "websocket" } ? K : never
}[keyof TRoutes & string]

/**
 * Resolve the allowed route-name union for `wsRoute` / `route.ws`.
 * Narrows to `protocol: "websocket"` routes when literal protocol metadata is present,
 * and falls back to `keyof TRoutes & string` for untyped `Record<string, RouteDefinition>` maps.
 */
export type WsRouteName<TRoutes extends Record<string, RouteDefinition>> = [WebSocketRouteNames<TRoutes>] extends [never] ? keyof TRoutes & string : WebSocketRouteNames<TRoutes>

/** Cache for compiled route patterns */
const patternCache = new Map<string, RegExp>()
/** Cache for wildcard route-name pattern matching */
const wildcardPatternCache = new Map<string, RegExp>()

/**
 * Compile a route path pattern to a regex for URL matching.
 * Results are cached for performance.
 *
 * @param path - Route path with {param} placeholders
 * @returns Compiled regex pattern
 */
function compilePattern(path: string): RegExp {
  const cached = patternCache.get(path)
  if (cached) return cached

  // Escape special regex characters except { }
  let pattern = path.replace(/[.*+?^$|()[\]]/g, "\\$&")
  // Replace {param} or {param:type} with matchers
  pattern = pattern.replace(/\{([^}]+)\}/g, (_match, paramSpec: string) => {
    const paramType = paramSpec.includes(":") ? paramSpec.split(":")[1] : "str"
    switch (paramType) {
      case "uuid":
        return "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
      case "path":
        return ".*"
      case "int":
        return "\\d+"
      default:
        return "[^/]+"
    }
  })
  const regex = new RegExp(`^${pattern}$`, "i")
  patternCache.set(path, regex)
  return regex
}

/** Compile a wildcard route pattern to regex for route-name matching. */
function compileWildcardPattern(pattern: string): RegExp {
  const cached = wildcardPatternCache.get(pattern)
  if (cached) return cached

  const escaped = pattern.replace(/[.+?^$|()[\]{}]/g, "\\$&")
  const regex = new RegExp(`^${escaped.replace(/\*/g, ".*")}$`)
  wildcardPatternCache.set(pattern, regex)
  return regex
}

/**
 * Format a route path with path and query parameters.
 */
export function formatRouteUrl<TRoutes extends Record<string, RouteDefinition>, TName extends keyof TRoutes & string>(
  name: TName,
  routes: TRoutes,
  params?: Record<string, unknown>,
  apiUrl?: string,
): string {
  const def = routes[name]
  if (!def) {
    throw new Error(`Route "${String(name)}" not found`)
  }
  let url = def.path.replace(/\{([^:}]+):[^}]+\}/g, "{$1}")

  if (params) {
    for (const param of def.pathParams) {
      const value = params[param]
      if (value !== undefined) {
        url = url.replaceAll(`{${param}}`, String(value))
      }
    }

    const queryParts: string[] = []
    for (const param of def.queryParams) {
      const value = params[param]
      if (value !== undefined) {
        queryParts.push(`${encodeURIComponent(param)}=${encodeURIComponent(String(value))}`)
      }
    }
    if (queryParts.length > 0) {
      url += `?${queryParts.join("&")}`
    }
  }

  return apiUrl ? `${apiUrl.replace(/\/$/, "")}${url}` : url
}

/**
 * Resolve a relative or HTTP URL into a WebSocket URL (`ws://` or `wss://`).
 */
export function resolveWsUrl(pathOrUrl: string, serverUrl?: string): string {
  if (/^wss?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl
  }
  if (/^https?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:")
  }
  const normalizedPath = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`
  if (serverUrl && serverUrl.trim()) {
    const cleanServer = serverUrl.trim().replace(/\/$/, "")
    if (/^wss?:\/\//i.test(cleanServer)) {
      return `${cleanServer}${normalizedPath}`
    }
    if (/^https?:\/\//i.test(cleanServer)) {
      return `${cleanServer.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:")}${normalizedPath}`
    }
    return `ws://${cleanServer}${normalizedPath}`
  }
  if (typeof window !== "undefined" && window.location && window.location.host) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:"
    return `${proto}//${window.location.host}${normalizedPath}`
  }
  return normalizedPath
}

/**
 * Generate a WebSocket URL (`ws://` or `wss://`) for a named WebSocket route.
 */
export function wsRoute<TRoutes extends Record<string, RouteDefinition>, TName extends string = WsRouteName<TRoutes>>(
  name: TName & WsRouteName<TRoutes>,
  routes: TRoutes,
  params?: Record<string, unknown>,
  options?: WsRouteOptions,
): string {
  const def = routes[name]
  if (!def) {
    throw new Error(`Route "${String(name)}" not found`)
  }
  const isWsRoute = def.protocol === "websocket" || (!def.protocol && def.methods.some((m) => m.toUpperCase() === "WS"))
  if (!isWsRoute) {
    throw new Error(`Route "${String(name)}" is not a WebSocket route`)
  }
  const formatted = formatRouteUrl(name, routes, params)
  return resolveWsUrl(formatted, options?.wsServerUrl ?? options?.serverUrl)
}

/**
 * Convert a URL to its corresponding route name.
 *
 * @param url - URL or path to match (query strings and hashes are stripped)
 * @param routes - The routeDefinitions object from generated routes
 * @returns The matching route name, or null if no match found
 *
 * @example
 * toRoute('/api/books', routeDefinitions)        // 'books'
 * toRoute('/api/books/123', routeDefinitions)    // 'book_detail'
 * toRoute('/unknown', routeDefinitions)          // null
 */
export function toRoute<T extends string>(url: string, routes: Record<T, RouteDefinition>): T | null {
  // Strip query string and hash
  const path = url.split("?")[0].split("#")[0]
  // Normalize: remove trailing slash except for root
  const normalized = path === "/" ? path : path.replace(/\/$/, "")

  for (const [name, def] of Object.entries(routes) as [T, RouteDefinition][]) {
    if (compilePattern(def.path).test(normalized)) {
      return name
    }
  }
  return null
}

/**
 * Get the current route name based on the browser URL.
 *
 * Returns null in SSR/non-browser environments.
 *
 * @param routes - The routeDefinitions object from generated routes
 * @returns Current route name, or null if no match or not in browser
 *
 * @example
 * // On page /api/books/123
 * currentRoute(routeDefinitions)  // 'book_detail'
 */
export function currentRoute<T extends string>(routes: Record<T, RouteDefinition>): T | null {
  if (typeof window === "undefined") return null
  return toRoute(window.location.pathname, routes)
}

/**
 * Check if a URL matches a route name or pattern.
 *
 * Supports wildcard patterns with `*` to match multiple routes.
 *
 * @param url - URL or path to check
 * @param pattern - Route name or pattern (e.g., 'books', 'book_*', '*_detail')
 * @param routes - The routeDefinitions object from generated routes
 * @returns True if the URL matches the route pattern
 *
 * @example
 * isRoute('/api/books', 'books', routeDefinitions)           // true
 * isRoute('/api/books/123', 'book_detail', routeDefinitions) // true
 * isRoute('/api/books/123', 'book_*', routeDefinitions)      // true (wildcard)
 * isRoute('/api/users', 'book_*', routeDefinitions)          // false
 */
export function isRoute<T extends string>(url: string, pattern: string, routes: Record<T, RouteDefinition>): boolean {
  const routeName = toRoute(url, routes)
  if (!routeName) return false
  const regex = compileWildcardPattern(pattern)
  return regex.test(routeName)
}

/**
 * Check if the current browser URL matches a route name or pattern.
 *
 * Supports wildcard patterns with `*` to match multiple routes.
 * Returns false in SSR/non-browser environments.
 *
 * @param pattern - Route name or pattern (e.g., 'books', 'book_*', '*_page')
 * @param routes - The routeDefinitions object from generated routes
 * @returns True if current URL matches the route pattern
 *
 * @example
 * // On page /books
 * isCurrentRoute('books_page', routeDefinitions)  // true
 * isCurrentRoute('book_*', routeDefinitions)      // false (no match)
 * isCurrentRoute('*_page', routeDefinitions)      // true (wildcard)
 */
export function isCurrentRoute<T extends string>(pattern: string, routes: Record<T, RouteDefinition>): boolean {
  const current = currentRoute(routes)
  if (!current) return false
  const regex = compileWildcardPattern(pattern)
  return regex.test(current)
}

/** @internal */
export function __getRouteWildcardRegexCacheSize(): number {
  return wildcardPatternCache.size
}

/** @internal */
export function __clearRouteHelperCachesForTest(): void {
  patternCache.clear()
  wildcardPatternCache.clear()
}

/**
 * Bound `route()` helper with `.ws()` attached for WebSocket route URL resolution.
 */
export interface BoundRouteFunction<T extends string, TRoutes extends Record<T, RouteDefinition> = Record<T, RouteDefinition>> {
  (name: T, params?: Record<string, unknown>): string
  ws: <TName extends string = WsRouteName<TRoutes>>(name: TName & WsRouteName<TRoutes>, params?: Record<string, unknown>, options?: WsRouteOptions) => string
}

/**
 * Route helpers interface returned by createRouteHelpers.
 */
export interface RouteHelpers<T extends string, TRoutes extends Record<T, RouteDefinition> = Record<T, RouteDefinition>> {
  /** Generate URL for a route (with `.ws()` attached for WebSocket routes) */
  route: BoundRouteFunction<T, TRoutes>
  /** Generate WebSocket URL (`ws://` or `wss://`) for a WebSocket route */
  wsRoute: <TName extends string = WsRouteName<TRoutes>>(name: TName & WsRouteName<TRoutes>, params?: Record<string, unknown>, options?: WsRouteOptions) => string
  /** Convert URL to route name */
  toRoute: (url: string) => T | null
  /** Get current route name (SSR-safe) */
  currentRoute: () => T | null
  /** Check if URL matches route pattern */
  isRoute: (url: string, pattern: string) => boolean
  /** Check if current URL matches route pattern */
  isCurrentRoute: (pattern: string) => boolean
}

/**
 * Create route helpers bound to a specific routeDefinitions object.
 *
 * This is the recommended way to use route helpers - it creates bound functions
 * so you don't need to pass routeDefinitions to every call.
 *
 * @param routes - The routeDefinitions object from your generated routes
 * @param defaultOptions - Optional default server URL options for `route.ws()`
 * @returns Object with bound route helper functions
 *
 * @example
 * ```ts
 * import { routeDefinitions } from '@/generated/routes'
 * import { createRouteHelpers } from 'litestar-vite-plugin/helpers'
 *
 * export const { route, isCurrentRoute, currentRoute, toRoute, isRoute } = createRouteHelpers(routeDefinitions)
 *
 * // Now use without passing routes:
 * if (isCurrentRoute('dashboard')) {
 *   // ...
 * }
 * ```
 */
export function createRouteHelpers<T extends string, TRoutes extends Record<T, RouteDefinition> = Record<T, RouteDefinition>>(
  routes: TRoutes,
  defaultOptions?: WsRouteOptions,
): RouteHelpers<T, TRoutes> {
  const defaultWsServer = defaultOptions?.wsServerUrl ?? defaultOptions?.serverUrl
  const boundWsRoute = <TName extends string = WsRouteName<TRoutes>>(name: TName & WsRouteName<TRoutes>, params?: Record<string, unknown>, options?: WsRouteOptions): string =>
    wsRoute(name, routes, params, {
      serverUrl: options?.wsServerUrl ?? options?.serverUrl ?? defaultWsServer,
    })

  const boundRoute = ((name: T, params?: Record<string, unknown>): string => formatRouteUrl(name, routes, params, defaultOptions?.serverUrl)) as BoundRouteFunction<T, TRoutes>
  boundRoute.ws = boundWsRoute

  return {
    route: boundRoute,
    wsRoute: boundWsRoute,
    toRoute: (url: string) => toRoute(url, routes),
    currentRoute: () => currentRoute(routes),
    isRoute: (url: string, pattern: string) => isRoute(url, pattern, routes),
    isCurrentRoute: (pattern: string) => isCurrentRoute(pattern, routes),
  }
}
