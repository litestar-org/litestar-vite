/**
 * Route utilities for Litestar applications.
 *
 * These helpers work with route metadata injected by Litestar:
 * - window.__LITESTAR_ROUTES__ (SPA mode with route injection)
 * - window.routes (legacy/Inertia mode)
 * - Generated routes from src/generated/routes.ts (typed routing)
 *
 * For typed routing, import from your generated routes instead:
 * ```ts
 * import { route, routes } from '@/generated/routes'
 * ```
 *
 * @module
 */

/**
 * Route definition from Litestar.
 */
export interface RouteDefinition {
  uri: string
  methods: string[]
  parameters?: string[]
  parameterTypes?: Record<string, string>
  queryParameters?: Record<string, string>
  component?: string
}

/**
 * Routes object mapping route names to definitions.
 */
export interface RoutesMap {
  routes: Record<string, RouteDefinition>
}

/**
 * Convenience alias for route names when using injected metadata.
 */
export type RouteName = keyof RoutesMap["routes"]

declare global {
  interface Window {
    __LITESTAR_ROUTES__?: RoutesMap
    routes?: Record<string, string>
    serverRoutes?: Record<string, string>
  }
  // eslint-disable-next-line no-var
  var routes: Record<string, string>
  // eslint-disable-next-line no-var
  var serverRoutes: Record<string, string>
}

declare global {
  interface ImportMeta {
    hot?: {
      on: (event: string, callback: (...args: unknown[]) => void) => void
      accept?: (cb?: () => void) => void
    }
  }
}

type RouteArg = string | number | boolean
type RouteArgs = Record<string, RouteArg> | RouteArg[]

/**
 * Get the routes object from the page.
 *
 * Checks multiple sources:
 * 1. window.__LITESTAR_ROUTES__ (SPA mode with full metadata)
 * 2. window.routes (legacy mode with just paths)
 *
 * @returns Routes map or null if not found
 */
export function getRoutes(): Record<string, string> | null {
  if (typeof window === "undefined") {
    return null
  }

  // Check for full route metadata (SPA mode)
  if (window.__LITESTAR_ROUTES__?.routes) {
    const routes: Record<string, string> = {}
    for (const [name, def] of Object.entries(window.__LITESTAR_ROUTES__.routes)) {
      routes[name] = def.uri
    }
    // Expose a descriptive alias for consumers
    window.serverRoutes = routes
    return routes
  }

  // Check for simple routes object (legacy/Inertia mode)
  if (window.routes) {
    return window.routes
  }

  // Check globalThis.routes
  if (typeof globalThis !== "undefined" && globalThis.routes) {
    return globalThis.routes
  }

  return null
}

/**
 * Generate a URL for a named route with parameters.
 *
 * @param routeName - The name of the route
 * @param args - Route parameters (object or array)
 * @returns The generated URL or "#" if route not found
 *
 * @example
 * ```ts
 * import { route } from 'litestar-vite-plugin/helpers'
 *
 * // Named parameters
 * route('user:detail', { user_id: 123 })  // "/users/123"
 *
 * // Positional parameters
 * route('user:detail', [123])  // "/users/123"
 * ```
 */
export function route(routeName: string, ...args: [RouteArgs?]): string {
  const routes = getRoutes()
  if (!routes) {
    console.error("Routes not available. Ensure route metadata is injected.")
    return "#"
  }

  let url = routes[routeName]
  if (!url) {
    console.error(`Route '${routeName}' not found.`)
    return "#"
  }

  const argTokens = url.match(/\{([^}]+)\}/g)

  if (!argTokens && args.length > 0 && args[0] !== undefined) {
    console.error(`Route '${routeName}' does not accept parameters.`)
    return "#"
  }

  if (!argTokens) {
    return new URL(url, window.location.origin).href
  }

  try {
    if (typeof args[0] === "object" && !Array.isArray(args[0])) {
      // Named parameters
      for (const token of argTokens) {
        let argName = token.slice(1, -1)
        // Handle {param:type} syntax
        if (argName.includes(":")) {
          argName = argName.split(":")[0]
        }

        const argValue = (args[0] as Record<string, unknown>)[argName]
        if (argValue === undefined) {
          throw new Error(`Missing parameter '${argName}'.`)
        }

        url = url.replace(token, String(argValue))
      }
    } else {
      // Positional parameters
      const argsArray = Array.isArray(args[0]) ? args[0] : Array.from(args)

      if (argTokens.length !== argsArray.length) {
        throw new Error(`Expected ${argTokens.length} parameters, got ${argsArray.length}.`)
      }

      argTokens.forEach((token, i) => {
        const argValue = argsArray[i]
        if (argValue === undefined) {
          throw new Error(`Missing parameter at position ${i}.`)
        }
        url = url.replace(token, String(argValue))
      })
    }
  } catch (error: unknown) {
    console.error(error instanceof Error ? error.message : String(error))
    return "#"
  }

  return new URL(url, window.location.origin).href
}

/**
 * Get the relative path portion of a URL.
 *
 * @param url - Full URL or path
 * @returns Relative path with query string and hash
 */
export function getRelativeUrlPath(url: string): string {
  try {
    const urlObject = new URL(url)
    return urlObject.pathname + urlObject.search + urlObject.hash
  } catch {
    return url
  }
}

/**
 * Convert a URL to a route name.
 *
 * @param url - URL to match
 * @returns Route name or null if no match
 *
 * @example
 * ```ts
 * toRoute('/users/123')  // "user:detail"
 * ```
 */
export function toRoute(url: string): string | null {
  const routes = getRoutes()
  if (!routes) {
    return null
  }

  const processedUrl = getRelativeUrlPath(url)
  const normalizedUrl = processedUrl === "/" ? processedUrl : processedUrl.replace(/\/$/, "")

  for (const [routeName, routePattern] of Object.entries(routes)) {
    const regexPattern = routePattern.replace(/\//g, "\\/").replace(/\{([^}]+)\}/g, (_, paramSpec) => {
      // Handle {param:type} syntax
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

    const regex = new RegExp(`^${regexPattern}$`)
    if (regex.test(normalizedUrl)) {
      return routeName
    }
  }

  return null
}

/**
 * Get the current route name based on window.location.
 *
 * @returns Current route name or null if no match
 */
export function currentRoute(): string | null {
  if (typeof window === "undefined") {
    return null
  }
  return toRoute(window.location.pathname)
}

/**
 * Check if a URL matches a route pattern.
 *
 * Supports wildcard patterns like "user:*" to match "user:list", "user:detail", etc.
 *
 * @param url - URL to check
 * @param routeName - Route name or pattern (supports * wildcards)
 * @returns True if the URL matches the route
 *
 * @example
 * ```ts
 * isRoute('/users/123', 'user:detail')  // true
 * isRoute('/users/123', 'user:*')       // true
 * ```
 */
export function isRoute(url: string, routeName: string): boolean {
  const routes = getRoutes()
  if (!routes) {
    return false
  }

  const processedUrl = getRelativeUrlPath(url)
  const normalizedUrl = processedUrl === "/" ? processedUrl : processedUrl.replace(/\/$/, "")

  // Convert route name pattern to regex
  const routeNameRegex = new RegExp(`^${routeName.replace(/\*/g, ".*")}$`)

  // Find all matching route names based on the pattern
  const matchingRouteNames = Object.keys(routes).filter((name) => routeNameRegex.test(name))

  for (const name of matchingRouteNames) {
    const routePattern = routes[name]
    const regexPattern = routePattern.replace(/\//g, "\\/").replace(/\{([^}]+)\}/g, (_, paramSpec) => {
      const paramType = paramSpec.includes(":") ? paramSpec.split(":")[1] : "str"

      switch (paramType) {
        case "uuid":
          return "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        case "path":
          return "(.*)"
        case "int":
          return "(\\d+)"
        default:
          return "([^/]+)"
      }
    })

    const regex = new RegExp(`^${regexPattern}$`)
    if (regex.test(normalizedUrl)) {
      return true
    }
  }

  return false
}

/**
 * Check if the current URL matches a route pattern.
 *
 * @param routeName - Route name or pattern (supports * wildcards)
 * @returns True if the current URL matches the route
 *
 * @example
 * ```ts
 * // On /users/123
 * isCurrentRoute('user:detail')  // true
 * isCurrentRoute('user:*')       // true
 * ```
 */
export function isCurrentRoute(routeName: string): boolean {
  const current = currentRoute()
  if (!current) {
    return false
  }

  const routeNameRegex = new RegExp(`^${routeName.replace(/\*/g, ".*")}$`)
  return routeNameRegex.test(current)
}

// Set up global functions for backward compatibility
if (typeof globalThis !== "undefined") {
  globalThis.routes = globalThis.routes || {}
  globalThis.serverRoutes = globalThis.serverRoutes || globalThis.routes
  ;(globalThis as Record<string, unknown>).route = route
  ;(globalThis as Record<string, unknown>).toRoute = toRoute
  ;(globalThis as Record<string, unknown>).currentRoute = currentRoute
  ;(globalThis as Record<string, unknown>).isRoute = isRoute
  ;(globalThis as Record<string, unknown>).isCurrentRoute = isCurrentRoute
}

// Keep serverRoutes fresh during Vite HMR when the plugin regenerates metadata/types
if (import.meta.hot) {
  import.meta.hot.on("litestar:types-updated", () => {
    if (typeof window === "undefined") {
      return
    }
    const updated = getRoutes()
    if (updated) {
      window.serverRoutes = updated
      window.routes = updated
    }
  })
}
