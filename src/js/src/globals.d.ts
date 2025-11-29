import type { RoutesMap, currentRoute, getRoutes, isCurrentRoute, isRoute, route, toRoute } from "./helpers/routes.js"

/**
 * Ambient declarations for browser globals injected by Litestar.
 *
 * Having these in a standalone .d.ts file ensures consumers get proper
 * typings as soon as they import the Vite plugin (e.g., in vite.config.ts),
 * without needing to import helpers within application code.
 */
declare global {
  interface Window {
    /**
     * Full route metadata injected by Litestar's SPA HTML transform.
     */
    __LITESTAR_ROUTES__?: RoutesMap
    /**
     * Simple name->path map used by legacy/Inertia modes.
     */
    routes?: Record<string, string>
    /**
     * Descriptive alias for the route map (name -> uri).
     */
    serverRoutes?: Record<string, string>
  }

  // Legacy globals (kept for backwards compatibility)
  // eslint-disable-next-line no-var
  var routes: Record<string, string> | undefined
  // eslint-disable-next-line no-var
  var serverRoutes: Record<string, string> | undefined

  interface GlobalThis {
    routes?: Record<string, string>
    serverRoutes?: Record<string, string>
    route?: typeof route
    toRoute?: typeof toRoute
    currentRoute?: typeof currentRoute
    isRoute?: typeof isRoute
    isCurrentRoute?: typeof isCurrentRoute
  }

  interface ImportMeta {
    hot?: {
      on: (event: string, callback: (...args: unknown[]) => void) => void
      accept?: (cb?: () => void) => void
    }
  }
}
