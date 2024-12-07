/* eslint-disable @typescript-eslint/no-explicit-any */
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

type RouteArg = string | number | boolean
type RouteArgs = Record<string, RouteArg> | RouteArg[]

export function route(routeName: string, ...args: [RouteArgs?]): string {
  let url = globalThis.routes[routeName]
  if (!url) {
    console.error(`URL '${routeName}' not found in routes.`)
    return "#" // Return "#" to indicate failure
  }

  const argTokens = url.match(/\{([^}]+):([^}]+)\}/g)

  if (!argTokens && args.length > 0) {
    console.error(`Invalid URL lookup: URL '${routeName}' does not expect arguments.`)
    return "#"
  }
  try {
    if (typeof args[0] === "object" && !Array.isArray(args[0])) {
      for (const token of argTokens ?? []) {
        let argName = token.slice(1, -1)
        if (argName.includes(":")) {
          argName = argName.split(":")[0]
        }

        const argValue = (args[0] as Record<string, unknown>)[argName]
        if (argValue === undefined) {
          throw new Error(`Invalid URL lookup: Argument '${argName}' was not provided.`)
        }

        url = url.replace(token, String(argValue))
      }
    } else {
      const argsArray = Array.isArray(args[0]) ? args[0] : Array.from(args)

      if (argTokens && argTokens.length !== argsArray.length) {
        throw new Error(`Invalid URL lookup: Wrong number of arguments; expected ${argTokens.length.toString()} arguments.`)
      }
      argTokens?.forEach((token, i) => {
        const argValue = argsArray[i]
        if (argValue === undefined) {
          throw new Error(`Missing argument at position ${i}`)
        }
        url = url.replace(token, argValue.toString())
      })
    }
  } catch (error: unknown) {
    console.error(error instanceof Error ? error.message : String(error))
    return "#"
  }

  const fullUrl = new URL(url, window.location.origin)
  return fullUrl.href
}

export function getRelativeUrlPath(url: string): string {
  try {
    const urlObject = new URL(url)
    return urlObject.pathname + urlObject.search + urlObject.hash
  } catch (e) {
    // If the URL is invalid or already a relative path, just return it as is
    return url
  }
}

function routePatternToRegex(pattern: string): RegExp {
  return new RegExp(`^${pattern.replace(/\*/g, ".*")}$`)
}

export function toRoute(url: string): string | null {
  const processedUrl = getRelativeUrlPath(url)
  const normalizedUrl = processedUrl === "/" ? processedUrl : processedUrl.replace(/\/$/, "")

  for (const [routeName, routePattern] of Object.entries(routes)) {
    const regexPattern = routePattern.replace(/\//g, "\\/").replace(/\{([^}]+):([^}]+)\}/g, (_, __, paramType) => {
      switch (paramType) {
        case "uuid":
          return "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        case "path":
          return ".*" // Matches any characters including forward slashes
        default:
          return "[^/]+" // Matches any characters except forward slashes
      }
    })

    const regex = new RegExp(`^${regexPattern}$`)
    if (regex.test(normalizedUrl)) {
      return routeName
    }
  }

  return null
}

export function currentRoute(): string | null {
  const currentUrl = window.location.pathname
  return toRoute(currentUrl)
}

export function isRoute(url: string, routeName: string): boolean {
  const processedUrl = getRelativeUrlPath(url)
  const normalizedUrl = processedUrl === "/" ? processedUrl : processedUrl.replace(/\/$/, "")
  const routeNameRegex = routePatternToRegex(routeName)

  // Find all matching route names based on the pattern
  const matchingRouteNames = Object.keys(routes).filter((name) => routeNameRegex.test(name))

  // For each matching route name, check if the URL matches its pattern
  for (const name of matchingRouteNames) {
    const routePattern = routes[name]
    const regexPattern = routePattern.replace(/\//g, "\\/").replace(/\{([^}]+):([^}]+)\}/g, (match, paramName, paramType) => {
      switch (paramType) {
        case "str":
          return "([^/]+)"
        case "path":
          return "(.*)"
        case "uuid":
          return "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
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
export function isCurrentRoute(routeName: string): boolean {
  const currentRouteName = currentRoute()
  if (!currentRouteName) {
    console.error("Could not match current window location to a named route.")
    return false
  }
  const routeNameRegex = routePatternToRegex(routeName)

  return routeNameRegex.test(currentRouteName)
}
declare global {
  // eslint-disable-next-line no-var
  var routes: { [key: string]: string }
  function route(routeName: string, ...args: [RouteArgs?]): string
  function toRoute(url: string): string | null
  function currentRoute(): string | null
  function isRoute(url: string, routeName: string): boolean
  function isCurrentRoute(routeName: string): boolean
}
globalThis.routes = globalThis.routes || {}
globalThis.route = route
globalThis.toRoute = toRoute
globalThis.currentRoute = currentRoute
globalThis.isRoute = isRoute
globalThis.isCurrentRoute = isCurrentRoute
