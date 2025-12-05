/**
 * Astro integration for Litestar-Vite.
 *
 * This integration enables seamless development with Astro as the frontend framework
 * and Litestar as the API backend. It provides:
 * - API proxy configuration for dev server
 * - Type generation integration (shares @hey-api/openapi-ts output)
 * - Route helper generation compatible with Astro's static paths
 *
 * @example
 * ```typescript
 * // astro.config.mjs
 * import { defineConfig } from 'astro/config';
 * import litestar from 'litestar-vite-plugin/astro';
 *
 * export default defineConfig({
 *   integrations: [
 *     litestar({
 *       apiProxy: 'http://localhost:8000',
 *       types: {
 *         enabled: true,
 *         output: 'src/generated/api',
 *       },
 *     }),
 *   ],
 * });
 * ```
 *
 * @module
 */

import { exec } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { promisify } from "node:util"
import colors from "picocolors"
import type { Plugin, ViteDevServer } from "vite"

import { resolveInstallHint } from "./install-hint.js"
import { debounce } from "./shared/debounce.js"

const execAsync = promisify(exec)

/**
 * Astro integration interface.
 * This is a minimal type definition to avoid requiring astro as a dependency.
 * When using this integration, Astro will be available in the project.
 */
/**
 * Astro config for updateConfig - partial types we support.
 */
interface AstroConfigPartial {
  server?: {
    port?: number
    host?: string | boolean
  }
  vite?: {
    plugins?: Plugin[]
    server?: {
      port?: number
      strictPort?: boolean
      proxy?: Record<string, unknown>
    }
  }
}

/**
 * AddressInfo from Node.js net module.
 */
interface AddressInfo {
  address: string
  family: string
  port: number
}

interface AstroIntegration {
  name: string
  hooks: {
    "astro:config:setup"?: (options: {
      config: unknown
      command: "dev" | "build" | "preview" | "sync"
      isRestart: boolean
      updateConfig: (newConfig: AstroConfigPartial) => unknown
      logger: AstroIntegrationLogger
    }) => void | Promise<void>
    "astro:server:setup"?: (options: { server: ViteDevServer; logger: AstroIntegrationLogger }) => void | Promise<void>
    "astro:server:start"?: (options: { address: AddressInfo; logger: AstroIntegrationLogger }) => void | Promise<void>
    "astro:build:start"?: (options: { logger: AstroIntegrationLogger }) => void | Promise<void>
  }
}

/**
 * Astro integration logger interface.
 */
interface AstroIntegrationLogger {
  info: (message: string) => void
  warn: (message: string) => void
  error: (message: string) => void
}

/**
 * Configuration for TypeScript type generation in Astro.
 */
export interface AstroTypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean

  /**
   * Path to output generated TypeScript types.
   * Relative to the Astro project root.
   *
   * @default 'src/types/api'
   */
  output?: string

  /**
   * Path where the OpenAPI schema is exported by Litestar.
   *
   * @default 'openapi.json'
   */
  openapiPath?: string

  /**
   * Path where route metadata is exported by Litestar.
   *
   * @default 'routes.json'
   */
  routesPath?: string

  /**
   * Generate Zod schemas in addition to TypeScript types.
   *
   * @default false
   */
  generateZod?: boolean

  /**
   * Generate SDK client functions for API calls.
   *
   * @default true
   */
  generateSdk?: boolean

  /**
   * Debounce time in milliseconds for type regeneration.
   *
   * @default 300
   */
  debounce?: number
}

/**
 * Configuration options for the Litestar Astro integration.
 */
export interface LitestarAstroConfig {
  /**
   * URL of the Litestar API backend for proxying requests during development.
   *
   * @example 'http://localhost:8000'
   * @default 'http://localhost:8000'
   */
  apiProxy?: string

  /**
   * API route prefix to proxy to the Litestar backend.
   * Requests matching this prefix will be forwarded to the apiProxy URL.
   *
   * @example '/api'
   * @default '/api'
   */
  apiPrefix?: string

  /**
   * Enable and configure TypeScript type generation.
   *
   * When set to `true`, enables type generation with default settings.
   * When set to an AstroTypesConfig object, enables type generation with custom settings.
   *
   * @default false
   */
  types?: boolean | AstroTypesConfig

  /**
   * Enable verbose logging for debugging.
   *
   * @default false
   */
  verbose?: boolean
}

/**
 * Resolved configuration with all defaults applied.
 */
interface ResolvedLitestarAstroConfig {
  apiProxy: string
  apiPrefix: string
  types: Required<AstroTypesConfig> | false
  verbose: boolean
  hotFile?: string
  proxyMode: "vite" | "direct" | "proxy" | null
  /** Port for Vite dev server (from VITE_PORT env or runtime config) */
  port?: number
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarAstroConfig = {}): ResolvedLitestarAstroConfig {
  const runtimeConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let port: number | undefined

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    port = Number.parseInt(envPort, 10)
    if (Number.isNaN(port)) {
      port = undefined
    }
  }

  if (runtimeConfigPath && fs.existsSync(runtimeConfigPath)) {
    try {
      const json = JSON.parse(fs.readFileSync(runtimeConfigPath, "utf-8")) as {
        bundleDir?: string
        hotFile?: string
        proxyMode?: "vite" | "direct" | "proxy" | null
        port?: number
      }
      const bundleDir = json.bundleDir ?? "public"
      const hot = json.hotFile ?? "hot"
      hotFile = path.resolve(process.cwd(), bundleDir, hot)
      proxyMode = json.proxyMode ?? "vite"
      // Runtime config port takes precedence over VITE_PORT env
      if (json.port !== undefined) {
        port = json.port
      }
    } catch {
      hotFile = undefined
    }
  }

  // Resolve types config
  let typesConfig: Required<AstroTypesConfig> | false = false

  if (config.types === true) {
    typesConfig = {
      enabled: true,
      output: "src/types/api",
      openapiPath: "openapi.json",
      routesPath: "routes.json",
      generateZod: false,
      generateSdk: true,
      debounce: 300,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    typesConfig = {
      enabled: config.types.enabled ?? true,
      output: config.types.output ?? "src/types/api",
      openapiPath: config.types.openapiPath ?? "openapi.json",
      routesPath: config.types.routesPath ?? "routes.json",
      generateZod: config.types.generateZod ?? false,
      generateSdk: config.types.generateSdk ?? true,
      debounce: config.types.debounce ?? 300,
    }
  }

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    types: typesConfig,
    verbose: config.verbose ?? false,
    hotFile,
    proxyMode,
    port,
  }
}

/**
 * Create a Vite plugin for API proxying and server configuration.
 */
function createProxyPlugin(config: ResolvedLitestarAstroConfig): Plugin {
  return {
    name: "litestar-astro-proxy",
    config() {
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, Astro might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
          // Set the port from Python config/env to ensure Astro uses the expected port
          // strictPort: true prevents Astro from auto-incrementing to a different port
          ...(config.port !== undefined
            ? {
                port: config.port,
                strictPort: true,
              }
            : {}),
          proxy: {
            [config.apiPrefix]: {
              target: config.apiProxy,
              changeOrigin: true,
              secure: false,
            },
          },
        },
      }
    },
  }
}

/**
 * Generate TypeScript route types from routes.json metadata.
 */
async function emitRouteTypes(routesPath: string, outputDir: string): Promise<void> {
  const contents = await fs.promises.readFile(routesPath, "utf-8")
  const json = JSON.parse(contents)

  const outDir = path.resolve(process.cwd(), outputDir)
  await fs.promises.mkdir(outDir, { recursive: true })
  const outFile = path.join(outDir, "routes.ts")

  const banner = `// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

`

  // Extract just the routes object from the full metadata
  const routesData = json.routes || json

  // Build route name union type and route map
  const routeNames = Object.keys(routesData)
  const routeNameType = routeNames.length > 0 ? routeNames.map((n) => `"${n}"`).join(" | ") : "never"

  // Build parameter types for each route
  const routeParamTypes: string[] = []
  for (const [name, data] of Object.entries(routesData)) {
    const routeData = data as { uri: string; parameters?: string[]; parameterTypes?: Record<string, string> }
    if (routeData.parameters && routeData.parameters.length > 0) {
      const params = routeData.parameters.map((p) => `${p}: string | number`).join("; ")
      routeParamTypes.push(`  "${name}": { ${params} }`)
    } else {
      routeParamTypes.push(`  "${name}": Record<string, never>`)
    }
  }

  const body = `/**
 * AUTO-GENERATED by litestar-vite.
 *
 * Exports:
 * - routesMeta: full route metadata
 * - routes: name -> uri map
 * - serverRoutes: alias of routes for clarity in apps
 * - route(): type-safe URL generator
 * - hasRoute(): type guard
 * - csrf helpers re-exported from litestar-vite-plugin/helpers
 *
 * @see https://litestar-vite.litestar.dev/
 */
export const routesMeta = ${JSON.stringify(json, null, 2)} as const

/**
 * Route name to URI mapping.
 */
export const routes = ${JSON.stringify(Object.fromEntries(Object.entries(routesData).map(([name, data]) => [name, (data as { uri: string }).uri])), null, 2)} as const

/**
 * Alias for server-injected route map (more descriptive for consumers).
 */
export const serverRoutes = routes

/**
 * All available route names.
 */
export type RouteName = ${routeNameType}

/**
 * Parameter types for each route.
 */
export interface RouteParams {
${routeParamTypes.join("\n")}
}

/**
 * Generate a URL for a named route with type-safe parameters.
 *
 * @param name - The route name
 * @param params - Route parameters (required if route has path parameters)
 * @returns The generated URL
 *
 * @example
 * \`\`\`ts
 * import { route } from '@/generated/routes'
 *
 * // Route without parameters
 * route('home')  // "/"
 *
 * // Route with parameters
 * route('user:detail', { user_id: 123 })  // "/users/123"
 * \`\`\`
 */
export function route<T extends RouteName>(
  name: T,
  ...args: RouteParams[T] extends Record<string, never> ? [] : [params: RouteParams[T]]
): string {
  let uri = routes[name] as string
  const params = args[0] as Record<string, string | number> | undefined

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      // Handle both {param} and {param:type} syntax
      uri = uri.replace(new RegExp(\`\\\\{$\{key}(?::[^}]+)?\\\\}\`, "g"), String(value))
    }
  }

  return uri
}

/**
 * Check if a route name exists.
 */
export function hasRoute(name: string): name is RouteName {
  return name in routes
}

declare global {
  interface Window {
    /**
     * Fully-typed route metadata injected by Litestar.
     */
    __LITESTAR_ROUTES__?: typeof routesMeta
    /**
     * Simple route map (name -> uri) for legacy consumers.
     */
    routes?: typeof routes
    serverRoutes?: typeof serverRoutes
  }
  // eslint-disable-next-line no-var
  var routes: typeof routes | undefined
  var serverRoutes: typeof serverRoutes | undefined
}

// Re-export helper functions from litestar-vite-plugin
// These work with the routes defined above
export { getCsrfToken, csrfHeaders, csrfFetch } from "litestar-vite-plugin/helpers"
`

  await fs.promises.writeFile(outFile, `${banner}${body}`, "utf-8")
}

/**
 * Create the type generation Vite plugin for Astro.
 */
function createTypeGenerationPlugin(typesConfig: Required<AstroTypesConfig>): Plugin {
  let server: ViteDevServer | null = null
  let isGenerating = false

  async function runTypeGeneration(): Promise<boolean> {
    if (isGenerating) {
      return false
    }

    isGenerating = true
    const startTime = Date.now()

    try {
      const openapiPath = path.resolve(process.cwd(), typesConfig.openapiPath)
      if (!fs.existsSync(openapiPath)) {
        console.log(colors.cyan("[litestar-astro]"), colors.yellow("OpenAPI schema not found:"), typesConfig.openapiPath)
        return false
      }

      console.log(colors.cyan("[litestar-astro]"), colors.dim("Generating TypeScript types..."))

      // Check for user config file first
      const projectRoot = process.cwd()
      const candidates = [path.resolve(projectRoot, "openapi-ts.config.ts"), path.resolve(projectRoot, "hey-api.config.ts"), path.resolve(projectRoot, ".hey-api.config.ts")]
      const configPath = candidates.find((p) => fs.existsSync(p)) || null

      let args: string[]
      if (configPath) {
        // Use user config file
        console.log(colors.cyan("[litestar-astro]"), colors.dim("Using config:"), configPath)
        args = ["@hey-api/openapi-ts", "--file", configPath]
      } else {
        // Build args with proper plugins
        args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

        const plugins = ["@hey-api/typescript", "@hey-api/schemas"]
        if (typesConfig.generateSdk) {
          plugins.push("@hey-api/sdk", "@hey-api/client-fetch")
        }
        if (typesConfig.generateZod) {
          plugins.push("zod")
        }
        if (plugins.length) {
          args.push("--plugins", ...plugins)
        }
      }

      await execAsync(`npx ${args.join(" ")}`, {
        cwd: projectRoot,
      })

      // Also generate route types if routes.json exists
      const routesPath = path.resolve(process.cwd(), typesConfig.routesPath)
      if (fs.existsSync(routesPath)) {
        await emitRouteTypes(routesPath, typesConfig.output)
      }

      const duration = Date.now() - startTime
      console.log(colors.cyan("[litestar-astro]"), colors.green("Types generated"), colors.dim(`in ${duration}ms`))

      // Notify HMR clients
      if (server) {
        server.ws.send({
          type: "custom",
          event: "litestar:types-updated",
          data: {
            output: typesConfig.output,
            timestamp: Date.now(),
          },
        })
      }

      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (message.includes("not found") || message.includes("ENOENT")) {
        console.log(colors.cyan("[litestar-astro]"), colors.yellow("@hey-api/openapi-ts not installed"), "- run:", resolveInstallHint())
      } else {
        console.error(colors.cyan("[litestar-astro]"), colors.red("Type generation failed:"), message)
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

  return {
    name: "litestar-astro-types",
    enforce: "pre",

    configureServer(devServer) {
      server = devServer
      console.log(colors.cyan("[litestar-astro]"), colors.dim("Watching for schema changes:"), colors.yellow(typesConfig.openapiPath))
    },

    async buildStart() {
      // Run type generation at build start if enabled and openapi.json exists
      if (typesConfig.enabled) {
        const openapiPath = path.resolve(process.cwd(), typesConfig.openapiPath)
        if (fs.existsSync(openapiPath)) {
          await runTypeGeneration()
        }
      }
    },

    handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const relativePath = path.relative(process.cwd(), file)
      const openapiPath = typesConfig.openapiPath.replace(/^\.\//, "")
      const routesPath = typesConfig.routesPath.replace(/^\.\//, "")

      if (relativePath === openapiPath || relativePath === routesPath || file.endsWith(openapiPath) || file.endsWith(routesPath)) {
        console.log(colors.cyan("[litestar-astro]"), colors.dim("Schema changed:"), colors.yellow(relativePath))
        debouncedRunTypeGeneration()
      }
    },
  }
}

/**
 * Litestar integration for Astro.
 *
 * This integration configures Astro to work seamlessly with a Litestar backend,
 * providing API proxying during development and type generation support.
 *
 * @param userConfig - Configuration options for the integration
 * @returns An Astro integration object
 *
 * @example
 * ```typescript
 * // astro.config.mjs
 * import { defineConfig } from 'astro/config';
 * import litestar from 'litestar-vite-plugin/astro';
 *
 * export default defineConfig({
 *   integrations: [
 *     litestar({
 *       apiProxy: 'http://localhost:8000',
 *       apiPrefix: '/api',
 *       types: {
 *         enabled: true,
 *         output: 'src/generated/api',
 *       },
 *     }),
 *   ],
 * });
 * ```
 *
 * @example Using with generated types
 * ```typescript
 * // src/pages/users/[id].astro
 * ---
 * import type { User } from '../generated/api/types.gen';
 * import { route } from '../generated/api/routes';
 *
 * const { id } = Astro.params;
 * const response = await fetch(route('users.show', { id }));
 * const user: User = await response.json();
 * ---
 *
 * <html>
 *   <body>
 *     <h1>{user.name}</h1>
 *   </body>
 * </html>
 * ```
 */
export default function litestarAstro(userConfig: LitestarAstroConfig = {}): AstroIntegration {
  const config = resolveConfig(userConfig)

  return {
    name: "litestar-vite",
    hooks: {
      "astro:config:setup": ({ updateConfig, logger, command }) => {
        if (config.verbose) {
          logger.info("Configuring Litestar integration")
          logger.info(`  API Proxy: ${config.apiProxy}`)
          logger.info(`  API Prefix: ${config.apiPrefix}`)
          if (config.types !== false) {
            logger.info(`  Types Output: ${config.types.output}`)
          }
          if (config.port !== undefined) {
            logger.info(`  Port: ${config.port}`)
          }
        }

        // Build the plugins array
        const plugins: Plugin[] = [createProxyPlugin(config)]

        // Add type generation plugin if enabled
        if (config.types !== false && config.types.enabled) {
          plugins.push(createTypeGenerationPlugin(config.types))
        }

        // Build the config update object
        const configUpdate: AstroConfigPartial = {
          vite: {
            plugins,
          },
        }

        // Set the Astro server port and host in dev mode
        // This must be done through Astro's server config, not just Vite's
        if (command === "dev") {
          configUpdate.server = {
            // Force IPv4 binding for consistency with Python proxy configuration
            host: "127.0.0.1",
            // Set port from Python config/env if provided
            ...(config.port !== undefined ? { port: config.port } : {}),
          }
          if (config.verbose) {
            logger.info(`Setting Astro server host to 127.0.0.1`)
            if (config.port !== undefined) {
              logger.info(`Setting Astro server port to ${config.port}`)
            }
          }
        }

        updateConfig(configUpdate)

        logger.info(`Litestar integration configured - proxying ${config.apiPrefix}/* to ${config.apiProxy}`)
      },

      "astro:server:setup": ({ server, logger }) => {
        if (config.verbose) {
          logger.info("Litestar dev server integration active")
        }

        // Log proxied requests if verbose
        if (config.verbose) {
          server.middlewares.use((req, _res, next) => {
            if (req.url?.startsWith(config.apiPrefix)) {
              logger.info(`Proxying: ${req.method} ${req.url} -> ${config.apiProxy}${req.url}`)
            }
            next()
          })
        }
      },

      // Write hotfile AFTER server starts listening (astro:server:start fires after listen())
      // Always write hotfile - proxy mode needs it for dynamic target discovery
      "astro:server:start": ({ address, logger }) => {
        if (config.hotFile) {
          // Normalize IPv4/IPv6 wildcards and localhost addresses to "localhost"
          const rawAddr = address.address
          const host = rawAddr === "::" || rawAddr === "::1" || rawAddr === "0.0.0.0" || rawAddr === "127.0.0.1" ? "localhost" : rawAddr
          const url = `http://${host}:${address.port}`
          fs.mkdirSync(path.dirname(config.hotFile), { recursive: true })
          fs.writeFileSync(config.hotFile, url)
          if (config.verbose) {
            logger.info(`Hotfile written: ${config.hotFile} -> ${url}`)
          }
        }
      },

      "astro:build:start": ({ logger }) => {
        logger.info("Building with Litestar integration")
        logger.info(`  Make sure your Litestar backend is accessible at: ${config.apiProxy}`)
      },
    },
  }
}
