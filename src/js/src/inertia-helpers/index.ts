/* eslint-disable @typescript-eslint/no-explicit-any */
export async function resolvePageComponent<T>(
    path: string | string[],
    pages: Record<string, Promise<T> | (() => Promise<T>)>
): Promise<T> {
    for (const p of Array.isArray(path) ? path : [path]) {
        const page = pages[p];

        if (typeof page === "undefined") {
            continue;
        }

        return typeof page === "function" ? page() : page;
    }

    throw new Error(`Page not found: ${path}`);
}


export function route(routeName: string, ...args: any[]): string  {
    let url = globalThis.routes[routeName];
    if (!url) {
        console.error(`URL '${routeName}' not found in routes.`);
        return "#"; // Return "#" to indicate failure
    }

    const argTokens = url.match(/\{([^}]+):([^}]+)\}/g);

    if (!argTokens && args.length > 0) {
        console.error(
            `Invalid URL lookup: URL '${routeName}' does not expect arguments.`
        );
        return "#";
    }
    try {
        if (typeof args[0] === "object" && !Array.isArray(args[0])) {
            argTokens?.forEach((token) => {
                let argName = token.slice(1, -1);
                if (argName.includes(":")) {
                    argName = argName.split(":")[1];
                }

                const argValue = (args[0] as { [key: string]: any })[argName];
                if (argValue === undefined) {
                    throw new Error(
                        `Invalid URL lookup: Argument '${argName}' was not provided.`
                    );
                }

                url = url.replace(token, argValue.toString());
            });
        } else {
            const argsArray = Array.isArray(args[0])
                ? args[0]
                : Array.prototype.slice.call(args);

            if (argTokens && argTokens.length !== argsArray.length) {
                throw new Error(
                    `Invalid URL lookup: Wrong number of arguments; expected ${argTokens.length.toString()} arguments.`
                );
            }
            argTokens?.forEach((token, i) => {
                const argValue = argsArray[i];
                url = url.replace(token, argValue.toString());
            });
        }
    } catch (error: any) {
        console.error(error.message);
        return "#";
    }

    const fullUrl = new URL(url, window.location.origin);
    return fullUrl.href;
}

export function getRelativeUrlPath(url: string): string {
    try {
        const urlObject = new URL(url);
        return urlObject.pathname + urlObject.search + urlObject.hash;
    } catch (e) {
        // If the URL is invalid or already a relative path, just return it as is
        return url;
    }
}
function routePatternToRegex(pattern: string): RegExp {
    return new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
}


export function toRoute(url: string): string | null  {
    url = getRelativeUrlPath(url)
    url = url === '/' ? url : url.replace(/\/$/, '');

    for (const routeName in routes) {
        const routePattern = routes[routeName];
        const regexPattern = routePattern.replace(/\//g, '\\/').replace(/\{([^}]+):([^}]+)\}/g, (match, paramName, paramType) => {
            // Create a regex pattern based on the parameter type
            switch (paramType) {
              case 'str':
              case 'path':
                return '([^/]+)'; // Match any non-slash characters
              case 'uuid':
                return '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'; // Match a UUID pattern
              default:
                return '([^/]+)'; // Default to match any non-slash characters
            }
          })


        const regex = new RegExp(`^${regexPattern}$`);
        if (regex.test(url)) {
          return routeName;
        }
      }

      return null; // No matching route found
}


export function currentRoute(): string | null  {
    const currentUrl = window.location.pathname;
    return toRoute(currentUrl)
}


export function isRoute(url: string, routeName: string): boolean  {
    url = getRelativeUrlPath(url)
    url = url === '/' ? url : url.replace(/\/$/, '');
    const routeNameRegex = routePatternToRegex(routeName);

    for (const routeName in routes) {
        if (routeNameRegex.test(routeName)) {
            const routePattern = routes[routeName];
            const regexPattern = routePattern.replace(/\//g, '\\/').replace(/\{([^}]+):([^}]+)\}/g, (match, paramName, paramType) => {
                switch (paramType) {
                    case 'str':
                    case 'path':
                        return '([^/]+)';
                    case 'uuid':
                        return '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
                    default:
                        return '([^/]+)';
                }
            });

            const regex = new RegExp(`^${regexPattern}$`);
            if (regex.test(url)) {
                return true;
            }
        }
    }

    return false;
}
export function isCurrentRoute(routeName: string): boolean {
    const currentRouteName = currentRoute()
    if (!currentRouteName) {
        console.error("Could not match current window location to a named route.");
        return false
    }
    const routeNameRegex = routePatternToRegex(routeName);

    return routeNameRegex.test(currentRouteName);
}
declare global {
    // eslint-disable-next-line no-var
    var routes: { [key: string]: string };
    function route(routeName: string, ...args: any[]): string
    function toRoute(url: string): string | null
    function currentRoute(): string | null
    function isRoute(url: string, routeName: string): boolean
    function isCurrentRoute(routeName: string): boolean
}
globalThis.routes = globalThis.routes || {};
globalThis.route = route
globalThis.toRoute = toRoute
globalThis.currentRoute = currentRoute
globalThis.isRoute = isRoute
globalThis.isCurrentRoute = isCurrentRoute
