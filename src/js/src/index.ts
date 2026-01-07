import fs from "node:fs"
import type { AddressInfo } from "node:net"
import path from "node:path"
import { fileURLToPath } from "node:url"
import colors from "picocolors"
import { loadEnv, type Plugin, type PluginOption, type ResolvedConfig, type SSROptions, type UserConfig, type ViteDevServer } from "vite"
import fullReload, { type Config as FullReloadConfig } from "vite-plugin-full-reload"

import { checkBackendAvailability, type LitestarMeta, loadLitestarMeta } from "./litestar-meta.js"
import { type BridgeSchema, readBridgeConfig } from "./shared/bridge-schema.js"
import { DEBOUNCE_MS } from "./shared/constants.js"
import { createLogger } from "./shared/logger.js"
import { createLitestarTypeGenPlugin } from "./shared/typegen-plugin.js"

/**
 * Configuration for TypeScript type generation.
 *
 * Type generation works as follows:
 * 1. Python's Litestar exports openapi.json and routes.json on startup (and reload)
 * 2. The Vite plugin watches these files for changes
 * 3. When they change, it runs @hey-api/openapi-ts to generate TypeScript types
 * 4. HMR event is sent to notify the client
 */
export interface TypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean
  /**
   * Path to output generated TypeScript types.
   *
   * @default 'src/generated'
   */
  output?: string
  /**
   * Path where the OpenAPI schema is exported by Litestar.
   * The Vite plugin watches this file and runs @hey-api/openapi-ts when it changes.
   *
   * @default 'src/generated/openapi.json'
   */
  openapiPath?: string
  /**
   * Path where route metadata is exported by Litestar.
   * The Vite plugin watches this file for route helper generation.
   *
   * @default 'src/generated/routes.json'
   */
  routesPath?: string
  /**
   * Optional path for the generated schemas.ts helper file.
   * Defaults to `${output}/schemas.ts` when not set.
   */
  schemasTsPath?: string
  /**
   * Path where Inertia page props metadata is exported by Litestar.
   * The Vite plugin watches this file for page props type generation.
   *
   * @default 'src/generated/inertia-pages.json'
   */
  pagePropsPath?: string
  /**
   * Generate Zod schemas in addition to TypeScript types.
   *
   * @default false
   */
  generateZod?: boolean
  /**
   * Generate a typed SDK client (fetch) in addition to types.
   *
   * @default true
   */
  generateSdk?: boolean
  /**
   * Generate typed routes.ts from routes.json metadata.
   *
   * Mirrors Python TypeGenConfig.generate_routes.
   *
   * @default true
   */
  generateRoutes?: boolean
  /**
   * Generate Inertia page props types from inertia-pages.json metadata.
   *
   * Mirrors Python TypeGenConfig.generate_page_props.
   *
   * @default true
   */
  generatePageProps?: boolean
  /**
   * Generate schemas.ts with ergonomic form/response type helpers.
   *
   * Creates helper types like FormInput<'api:login'> and FormResponse<'api:login', 201>
   * that wrap hey-api generated types with cleaner DX.
   *
   * @default true
   */
  generateSchemas?: boolean
  /**
   * Register route() function globally on window object.
   *
   * When true, the generated routes.ts will include code that registers
   * the type-safe route() function on `window.route`, similar to Laravel's
   * Ziggy library. This allows using route() without imports.
   *
   * @default false
   */
  globalRoute?: boolean
  /**
   * Debounce time in milliseconds for type regeneration.
   * Prevents regeneration from running too frequently when
   * multiple files are written in quick succession.
   *
   * @default 300
   */
  debounce?: number
}

export interface PluginConfig {
  /**
   * The path or paths of the entry points to compile.
   */
  input: string | string[]
  /**
   * The base path to use for all asset URLs.
   *
   * @default '/static/'
   */
  assetUrl?: string
  /**
   * Optional asset URL to use only during production builds.
   *
   * This is typically derived from Python DeployConfig.asset_url and written into `.litestar.json`
   * as `deployAssetUrl`. It is only used when `command === "build"`.
   */
  deployAssetUrl?: string
  /**
   * The public directory where all compiled/bundled assets should be written.
   *
   * @default 'public/dist'
   */
  bundleDir?: string
  /**
   * Directory for static, unprocessed assets.
   *
   * This maps to Vite's `publicDir` option, but is named `staticDir` in this
   * plugin to avoid confusion with Litestar's `bundleDir` (often `public`).
   *
   * Note: The Litestar plugin defaults this to `${resourceDir}/public` to avoid
   * Vite's `publicDir` colliding with Litestar's `bundleDir`.
   *
   * @default `${resourceDir}/public`
   */
  staticDir?: string
  /**
   * Litestar's public assets directory.  These are the assets that Vite will serve when developing.
   *
   * @default 'src'
   */
  resourceDir?: string

  /**
   * The path to the "hot" file.
   *
   * @default `${bundleDir}/hot`
   */
  hotFile?: string

  /**
   * The path of the SSR entry point.
   */
  ssr?: string | string[]

  /**
   * The directory where the SSR bundle should be written.
   *
   * @default `${resourceDir}/bootstrap/ssr`
   */
  ssrOutDir?: string

  /**
   * Configuration for performing full page refresh on python (or other) file changes.
   *
   * {@link https://github.com/ElMassimo/vite-plugin-full-reload}
   * @default false
   */
  refresh?: boolean | string | string[] | RefreshConfig | RefreshConfig[]

  /**
   * Utilize TLS certificates.
   *
   * @default null
   */
  detectTls?: string | boolean | null
  /**
   * Automatically detect the index.html file.
   *
   * @default true
   */
  autoDetectIndex?: boolean
  /**
   * Enable Inertia mode.
   *
   * In Inertia apps, the backend (Litestar) serves all HTML responses.
   * When enabled, direct access to the Vite dev server will show a placeholder
   * page directing users to access the app through the backend (even if an
   * index.html exists for the backend to render).
   *
   * Auto-detected from `.litestar.json` when mode is "inertia".
   *
   * @default false (auto-detected from .litestar.json)
   */
  inertiaMode?: boolean
  /**
   * Transform the code while serving.
   */
  transformOnServe?: (code: string, url: DevServerUrl) => string
  /**
   * Enable and configure TypeScript type generation.
   *
   * Configuration priority (highest to lowest):
   * 1. Explicit vite.config.ts value - ALWAYS wins
   * 2. .litestar.json value - used if no explicit config
   * 3. Hardcoded defaults - fallback if nothing else
   *
   * When set to `"auto"` (recommended): reads all config from `.litestar.json`.
   * If `.litestar.json` is missing, type generation is disabled.
   *
   * When set to `true`: enables type generation with hardcoded defaults.
   * When set to `false`: disables type generation entirely.
   * When set to a TypesConfig object: uses your explicit settings.
   *
   * When not specified (undefined): behaves like `"auto"` - reads from
   * `.litestar.json` if present, otherwise disabled.
   *
   * @example
   * ```ts
   * // Recommended: auto-read from .litestar.json (simplest)
   * litestar({ input: 'src/main.ts' })
   *
   * // Explicit auto mode
   * litestar({ input: 'src/main.ts', types: 'auto' })
   *
   * // Force enable with hardcoded defaults (ignores .litestar.json)
   * litestar({ input: 'src/main.ts', types: true })
   *
   * // Force disable
   * litestar({ input: 'src/main.ts', types: false })
   *
   * // Manual override (ignores .litestar.json for types)
   * litestar({
   *   input: 'src/main.ts',
   *   types: {
   *     enabled: true,
   *     output: 'src/api/types',
   *     generateZod: true
   *   }
   * })
   * ```
   *
   * @default undefined (auto-detect from .litestar.json)
   */
  types?: boolean | "auto" | TypesConfig
  /**
   * JavaScript runtime executor for package commands.
   * Used when running tools like @hey-api/openapi-ts.
   *
   * This is typically auto-detected from Python config via LITESTAR_VITE_RUNTIME env var,
   * but can be overridden here for JS-only projects or specific needs.
   *
   * @default undefined (uses LITESTAR_VITE_RUNTIME env or 'node')
   */
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
}

interface RefreshConfig {
  paths: string[]
  config?: FullReloadConfig
}

/**
 * Resolved plugin configuration with all defaults applied.
 * Note: `types` is resolved to `Required<TypesConfig> | false` instead of `boolean | TypesConfig`
 * Note: `executor` remains optional - undefined means auto-detect from env
 * Note: `inertiaMode` is resolved to boolean (auto-detected from .litestar.json mode)
 */
interface ResolvedPluginConfig extends Omit<Required<PluginConfig>, "types" | "executor" | "inertiaMode" | "deployAssetUrl"> {
  types: Required<TypesConfig> | false
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
  /** Optional asset URL to use for production builds (overrides assetUrl during build) */
  deployAssetUrl?: string
  /** Whether in Inertia mode (backend serves HTML, not Vite) */
  inertiaMode: boolean
  /** Whether .litestar.json was found (used for validation warnings) */
  hasPythonConfig: boolean
}

// Bridge schema is defined in ./shared/bridge-schema.ts

// Note: We intentionally avoid exporting Vite types to prevent version conflicts.
// The plugin returns Plugin[] internally but uses `any[]` in the public API to avoid
// type leakage across different Vite versions (6.x, 7.x). This follows the pragmatic
// approach used by other multi-version plugins.

type DevServerUrl = `${"http" | "https"}://${string}:${number}`

let exitHandlersBound = false
let warnedMissingRuntimeConfig = false

const refreshPaths = ["src/**", "resources/**", "assets/**"].filter((path) => fs.existsSync(path.replace(/\*\*$/, "")))

/**
 * Litestar plugin for Vite.
 *
 * @param config - A config object or relative path(s) of the scripts to be compiled.
 * @returns An array of Vite plugins. Return type is `any[]` to avoid cross-version type conflicts.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function litestar(config: string | string[] | PluginConfig): any[] {
  const pluginConfig = resolvePluginConfig(config)

  const plugins: Plugin[] = [resolveLitestarPlugin(pluginConfig), ...(resolveFullReloadConfig(pluginConfig) as Plugin[])]

  // Add type generation plugin if enabled
  if (pluginConfig.types !== false && pluginConfig.types.enabled) {
    plugins.push(
      createLitestarTypeGenPlugin(pluginConfig.types, {
        pluginName: "litestar-vite-types",
        frameworkName: "litestar-vite",
        sdkClientPlugin: "@hey-api/client-axios",
        executor: pluginConfig.executor,
        hasPythonConfig: pluginConfig.hasPythonConfig,
      }),
    )
  }

  return plugins
}

/**
 * Resolve the index.html path to use for the Vite server.
 */
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: ResolvedPluginConfig): Promise<string | null> {
  // NOTE: We no longer return null for inertiaMode here.
  // Vite needs to see an index.html to register internal virtual modules like @vite/client.
  // The middleware below handles serving the placeholder for inertiaMode instead.
  // See: https://github.com/vitejs/vite/discussions/2418

  if (!pluginConfig.autoDetectIndex) {
    return null
  }

  // Use server.config.root which is the resolved root directory
  const root = server.config.root
  const possiblePaths = [
    path.join(root, "index.html"),
    path.join(root, pluginConfig.resourceDir.replace(/^\//, ""), "index.html"), // Ensure resourceDir path is relative to root
    path.join(root, pluginConfig.staticDir.replace(/^\//, ""), "index.html"),
    path.join(root, pluginConfig.bundleDir.replace(/^\//, ""), "index.html"),
  ]
  // console.log("Checking paths:", possiblePaths); // Debug log

  for (const indexPath of possiblePaths) {
    try {
      // Use async access check
      await fs.promises.access(indexPath)
      // console.log("Found index.html at:", indexPath); // Debug log
      return indexPath
    } catch {
      // File doesn't exist at this path, continue checking
    }
  }
  // console.log("index.html not found in checked paths."); // Debug log
  return null
}

/**
 * Resolve the Litestar Plugin configuration.
 */
function normalizeAppUrl(appUrl: string | undefined, _fallbackPort?: string): { url: string | null; note?: string } {
  if (!appUrl || appUrl === "__litestar_app_url_missing__") {
    return { url: null, note: "APP_URL missing" }
  }
  try {
    const url = new URL(appUrl)

    const rebuilt = url.origin + (url.pathname === "/" ? "" : url.pathname) + (url.search ?? "") + (url.hash ?? "")

    return { url: rebuilt }
  } catch {
    return { url: null, note: "APP_URL invalid" }
  }
}

function resolveLitestarPlugin(pluginConfig: ResolvedPluginConfig): Plugin {
  let viteDevServerUrl: DevServerUrl
  let resolvedConfig: ResolvedConfig
  let userConfig: UserConfig
  let litestarMeta: LitestarMeta = {}
  let shuttingDown = false
  const pythonDefaults = loadPythonDefaults()
  const logger = createLogger(pythonDefaults?.logging)
  const defaultAliases: Record<string, string> = {
    "@": `/${pluginConfig.resourceDir.replace(/^\/+/, "").replace(/\/+$/, "")}/`,
  }

  return {
    name: "litestar",
    enforce: "post",
    config: (config, { command, mode }) => {
      userConfig = config
      const ssr = !!userConfig.build?.ssr
      const env = loadEnv(mode, userConfig.envDir || process.cwd(), "")
      const runtimeAssetUrl = normalizeAssetUrl(env.ASSET_URL || pluginConfig.assetUrl)
      const buildAssetUrl = pluginConfig.deployAssetUrl ?? runtimeAssetUrl
      const serverConfig = command === "serve" ? (resolveDevelopmentEnvironmentServerConfig(pluginConfig.detectTls) ?? resolveEnvironmentServerConfig(env)) : undefined

      const withProxyErrorSilencer = (proxyConfig: Record<string, any> | undefined) => {
        if (!proxyConfig) return undefined
        return Object.fromEntries(
          Object.entries(proxyConfig).map(([key, value]) => {
            if (typeof value !== "object" || value === null) {
              return [key, value]
            }
            const existingConfigure = value.configure
            return [
              key,
              {
                ...value,
                configure(proxy: any, opts: any) {
                  proxy.on("error", (err: any) => {
                    const msg = String(err?.message ?? "")
                    if (shuttingDown || msg.includes("ECONNREFUSED") || msg.includes("ECONNRESET") || msg.includes("socket hang up")) {
                      return
                    }
                  })
                  if (typeof existingConfigure === "function") {
                    existingConfigure(proxy, opts)
                  }
                },
              },
            ]
          }),
        )
      }
      const devBase = pluginConfig.assetUrl.startsWith("/") ? pluginConfig.assetUrl : pluginConfig.assetUrl.replace(/\/+$/, "")

      ensureCommandShouldRunInEnvironment(command, env, mode)

      return {
        base: userConfig.base ?? (command === "build" ? resolveBase(pluginConfig, buildAssetUrl) : devBase),
        publicDir: userConfig.publicDir ?? pluginConfig.staticDir ?? false,
        clearScreen: false,
        build: {
          manifest: userConfig.build?.manifest ?? (ssr ? false : "manifest.json"),
          ssrManifest: userConfig.build?.ssrManifest ?? (ssr ? "ssr-manifest.json" : false),
          outDir: userConfig.build?.outDir ?? resolveOutDir(pluginConfig, ssr),
          rollupOptions: {
            input: userConfig.build?.rollupOptions?.input ?? resolveInput(pluginConfig, ssr),
          },
          assetsInlineLimit: userConfig.build?.assetsInlineLimit ?? 0,
        },
        server: {
          origin: userConfig.server?.origin ?? "__litestar_vite_placeholder__",
          // Auto-configure HMR to use a path that routes through Litestar proxy
          // Note: Vite automatically prepends `base` to `hmr.path`, so we just use "vite-hmr"
          // Result: base="/static/" + path="vite-hmr" = "/static/vite-hmr"
          hmr:
            userConfig.server?.hmr === false
              ? false
              : {
                  path: "vite-hmr",
                  ...(serverConfig?.hmr ?? {}),
                  ...(userConfig.server?.hmr === true ? {} : userConfig.server?.hmr),
                },
          // Auto-configure proxy to forward API requests to Litestar backend
          // This allows the app to work when accessing Vite directly (not through Litestar proxy)
          // Only proxies /api and /schema routes - everything else is handled by Vite
          proxy: withProxyErrorSilencer(
            userConfig.server?.proxy ??
              (env.APP_URL
                ? {
                    "/api": {
                      target: env.APP_URL,
                      changeOrigin: true,
                    },
                    "/schema": {
                      target: env.APP_URL,
                      changeOrigin: true,
                    },
                  }
                : undefined),
          ),
          // Always respect VITE_PORT when set by Python (regardless of VITE_ALLOW_REMOTE)
          ...(process.env.VITE_PORT
            ? {
                port: userConfig.server?.port ?? Number.parseInt(process.env.VITE_PORT),
                strictPort: userConfig.server?.strictPort ?? true,
              }
            : undefined),
          // VITE_ALLOW_REMOTE controls host binding (0.0.0.0 for remote access)
          // Also sets port/strictPort for backwards compatibility when VITE_PORT not set
          ...(process.env.VITE_ALLOW_REMOTE
            ? {
                host: userConfig.server?.host ?? "0.0.0.0",
                ...(process.env.VITE_PORT
                  ? {} // port already set above
                  : {
                      port: userConfig.server?.port ?? 5173,
                      strictPort: userConfig.server?.strictPort ?? true,
                    }),
              }
            : undefined),
          ...(serverConfig
            ? {
                host: userConfig.server?.host ?? serverConfig.host,
                https: userConfig.server?.https ?? serverConfig.https,
              }
            : undefined),
        },
        resolve: {
          alias: Array.isArray(userConfig.resolve?.alias)
            ? [
                ...(userConfig.resolve?.alias ?? []),
                ...Object.keys(defaultAliases).map((alias) => ({
                  find: alias,
                  replacement: defaultAliases[alias],
                })),
              ]
            : {
                ...defaultAliases,
                ...userConfig.resolve?.alias,
              },
        },
        ssr: {
          noExternal: noExternalInertiaHelpers(userConfig),
        },
        // Explicitly set appType if you know you're serving an SPA index.html
        // appType: 'spa', // Try adding this - might simplify things if appropriate
      }
    },
    async configResolved(config) {
      resolvedConfig = config
      // Ensure base ends with / for dev server if not empty
      if (resolvedConfig.command === "serve" && resolvedConfig.base && !resolvedConfig.base.endsWith("/")) {
        resolvedConfig = {
          ...resolvedConfig,
          base: `${resolvedConfig.base}/`,
        }
      }

      // Early validation: warn if running serve without backend config
      if (resolvedConfig.command === "serve" && !pluginConfig.hasPythonConfig && !warnedMissingRuntimeConfig) {
        warnedMissingRuntimeConfig = true
        if (typeof resolvedConfig.logger?.warn === "function") {
          resolvedConfig.logger.warn(formatMissingConfigWarning())
        }
      }

      // Validate resource directory exists (if explicitly configured)
      const resourceDirPath = path.resolve(resolvedConfig.root, pluginConfig.resourceDir)
      if (!fs.existsSync(resourceDirPath) && typeof resolvedConfig.logger?.warn === "function") {
        resolvedConfig.logger.warn(`${colors.cyan("litestar-vite")} ${colors.yellow("Resource directory not found:")} ${pluginConfig.resourceDir}`)
      }

      const hint = pluginConfig.types !== false ? pluginConfig.types.routesPath : undefined
      litestarMeta = await loadLitestarMeta(resolvedConfig, hint)
    },
    transform(code: string, _id: string): string | undefined {
      // Added '_id' for context
      // Avoid transforming unrelated files during serve if placeholder isn't present
      if (resolvedConfig.command === "serve" && code.includes("__litestar_vite_placeholder__")) {
        // Debug log transformation
        // console.log(`Transforming ${id} with dev server URL: ${viteDevServerUrl}`);
        const transformedCode = code.replace(/__litestar_vite_placeholder__/g, viteDevServerUrl)
        // Apply user transform *only* if the placeholder was found and replaced
        return pluginConfig.transformOnServe(transformedCode, viteDevServerUrl)
      }
      return undefined
    },
    async configureServer(server) {
      const envDir = resolvedConfig.envDir || process.cwd()
      const envWithApp = loadEnv(resolvedConfig.mode, envDir, "APP_URL")
      const rawAppUrl = envWithApp.APP_URL ?? "__litestar_app_url_missing__"
      const normalizedAppUrl = normalizeAppUrl(rawAppUrl, envWithApp.LITESTAR_PORT)
      const appUrl = normalizedAppUrl.url ?? rawAppUrl

      // Resolve hotFile path relative to bundleDir (unless user already included it).
      // This keeps JS + Python aligned (Python reads bundleDir/hot by default).
      if (pluginConfig.hotFile && !path.isAbsolute(pluginConfig.hotFile)) {
        const normalizedHot = pluginConfig.hotFile.replace(/^\/+/, "")
        const normalizedBundle = pluginConfig.bundleDir?.replace(/^\/+/, "").replace(/\/+$/, "")
        const hotUnderBundle = normalizedBundle ? normalizedHot.startsWith(`${normalizedBundle}/`) : false
        const baseDir = hotUnderBundle ? server.config.root : path.resolve(server.config.root, normalizedBundle ?? "")
        pluginConfig.hotFile = path.resolve(baseDir, normalizedHot)
      }

      // Find index.html path *once* when server starts for logging purposes
      const initialIndexPath = await findIndexHtmlPath(server, pluginConfig)

      server.httpServer?.once("listening", () => {
        const address = server.httpServer?.address()

        const isAddressInfo = (x: string | AddressInfo | null | undefined): x is AddressInfo => typeof x === "object"
        if (isAddressInfo(address)) {
          viteDevServerUrl = userConfig.server?.origin ? (userConfig.server.origin as DevServerUrl) : resolveDevServerUrl(address, server.config, userConfig)
          fs.mkdirSync(path.dirname(pluginConfig.hotFile), { recursive: true })
          fs.writeFileSync(pluginConfig.hotFile, viteDevServerUrl)

          // Check backend availability and log status
          // Delay to allow Litestar to start when launched together via `litestar assets serve`
          setTimeout(async () => {
            // Skip banner in quiet mode
            if (logger.config.level === "quiet") return

            const litestarVersion = litestarMeta.litestarVersion ?? process.env.LITESTAR_VERSION ?? "unknown"

            // Retry backend check a few times when started together with Litestar
            let backendStatus = await checkBackendAvailability(appUrl)
            if (!backendStatus.available) {
              // Wait a bit and retry - Litestar may still be starting
              for (let i = 0; i < 3 && !backendStatus.available; i++) {
                await new Promise((resolve) => setTimeout(resolve, 500))
                backendStatus = await checkBackendAvailability(appUrl)
              }
            }

            // Combined LITESTAR + VITE banner (replaces separate Vite banner)
            resolvedConfig.logger.info(`\n  ${colors.red(`${colors.bold("LITESTAR")} ${litestarVersion}`)}`)
            resolvedConfig.logger.info("")

            // Mode - simplified display
            if (pluginConfig.inertiaMode) {
              resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Mode")}:       Inertia`)
            } else if (initialIndexPath) {
              const relIndexPath = logger.path(initialIndexPath, server.config.root)
              resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Mode")}:       SPA (${colors.cyan(relIndexPath)})`)
            } else {
              resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Mode")}:       Litestar`)
            }

            // App URL with backend status - this is the main URL users care about
            if (backendStatus.available) {
              resolvedConfig.logger.info(
                `  ${colors.green("➜")}  ${colors.bold("App URL")}:    ${colors.cyan(appUrl.replace(/:(\d+)/, (_, port) => `:${colors.bold(port)}`))} ${colors.green("✓")}`,
              )
            } else {
              resolvedConfig.logger.info(
                `  ${colors.yellow("➜")}  ${colors.bold("App URL")}:    ${colors.cyan(appUrl.replace(/:(\d+)/, (_, port) => `:${colors.bold(port)}`))} ${colors.yellow("⚠")}`,
              )
            }

            // Dev server URL (where Vite is actually running)
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Dev Server")}: ${colors.cyan(viteDevServerUrl)}`)

            // Type generation status - use relative path
            if (pluginConfig.types !== false && pluginConfig.types.enabled) {
              const openapiExists = fs.existsSync(path.resolve(process.cwd(), pluginConfig.types.openapiPath))
              const routesExists = fs.existsSync(path.resolve(process.cwd(), pluginConfig.types.routesPath))
              const relTypesOutput = logger.path(pluginConfig.types.output, process.cwd())

              if (openapiExists || routesExists) {
                resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Type Gen")}:   ${colors.dim(`${relTypesOutput}/`)}`)
              } else {
                resolvedConfig.logger.info(`  ${colors.yellow("➜")}  ${colors.bold("Type Gen")}:   ${colors.yellow("waiting")} ${colors.dim("(no schema files yet)")}`)
              }
            }

            // Backend status warnings/hints (only when backend is not available)
            if (!backendStatus.available) {
              resolvedConfig.logger.info("")
              resolvedConfig.logger.info(`  ${colors.yellow("⚠")}  ${colors.bold("Backend Status")}`)

              if (backendStatus.error === "APP_URL not configured" || normalizedAppUrl.note) {
                resolvedConfig.logger.info(`     ${colors.dim("APP_URL environment variable is not set.")}`)
                resolvedConfig.logger.info(`     ${colors.dim("Set APP_URL in your .env file or environment.")}`)
                if (normalizedAppUrl.note === "APP_URL invalid") {
                  resolvedConfig.logger.info(`     ${colors.dim(`Current APP_URL is invalid: ${rawAppUrl}`)}`)
                }
              } else {
                resolvedConfig.logger.info(`     ${colors.dim(backendStatus.error ?? "Backend not available")}`)
                resolvedConfig.logger.info("")
                resolvedConfig.logger.info(`     ${colors.bold("To start your Litestar app:")}`)
                resolvedConfig.logger.info(`     ${colors.cyan("litestar run")} ${colors.dim("or")} ${colors.cyan("uvicorn app:app --reload")}`)
              }

              resolvedConfig.logger.info("")
              resolvedConfig.logger.info(`     ${colors.dim("The Vite dev server is running and will serve assets.")}`)
              resolvedConfig.logger.info(`     ${colors.dim("Start your Litestar backend to view the full application.")}`)
            }

            resolvedConfig.logger.info("")
          }, 100)
        }
      })

      // Clean up hot file on exit
      if (!exitHandlersBound) {
        const clean = () => {
          if (pluginConfig.hotFile && fs.existsSync(pluginConfig.hotFile)) {
            // Check hotFile exists
            fs.rmSync(pluginConfig.hotFile)
          }
        }
        process.on("exit", clean)
        process.on("SIGINT", () => {
          shuttingDown = true
          process.exit()
        })
        process.on("SIGTERM", () => {
          shuttingDown = true
          process.exit()
        })
        process.on("SIGHUP", () => {
          shuttingDown = true
          process.exit()
        })
        exitHandlersBound = true
      }

      // Add PRE-middleware to intercept requests BEFORE Vite's base redirect
      // This allows serving index.html (or placeholder) at "/" while using a different base for assets.
      server.middlewares.use(async (req, res, next) => {
        const requestUrl = req.originalUrl ?? req.url ?? "/"
        const requestPath = requestUrl.split("?")[0]
        const isRootRequest = requestPath === "/" || requestPath === "/index.html"

        if (requestPath === "/__litestar__/transform-index") {
          if (req.method !== "POST") {
            res.statusCode = 405
            res.setHeader("Content-Type", "text/plain")
            res.end("Method Not Allowed")
            return
          }

          const readBody = async (): Promise<string> =>
            new Promise((resolve, reject) => {
              let data = ""
              req.on("data", (chunk) => {
                data += chunk
              })
              req.on("end", () => resolve(data))
              req.on("error", (err) => reject(err))
            })

          try {
            const body = await readBody()
            const payload = JSON.parse(body) as { html?: string; url?: string }
            if (!payload.html || typeof payload.html !== "string") {
              res.statusCode = 400
              res.setHeader("Content-Type", "text/plain")
              res.end("Invalid payload")
              return
            }

            const url = typeof payload.url === "string" && payload.url ? payload.url : "/"
            const transformedHtml = await server.transformIndexHtml(url, payload.html, url)
            res.statusCode = 200
            res.setHeader("Content-Type", "text/html")
            res.end(transformedHtml)
          } catch (e) {
            resolvedConfig.logger.error(`Error transforming index.html: ${e instanceof Error ? e.message : e}`)
            res.statusCode = 500
            res.setHeader("Content-Type", "text/plain")
            res.end("Error transforming HTML")
          }
          return
        }

        if (!isRootRequest) {
          next()
          return
        }

        // In Inertia mode, always show the dev-server placeholder on the Vite port.
        if (pluginConfig.inertiaMode) {
          try {
            const placeholderPath = path.join(dirname(), "dev-server-index.html")
            const placeholderContent = await fs.promises.readFile(placeholderPath, "utf-8")
            res.statusCode = 200
            res.setHeader("Content-Type", "text/html")
            res.end(placeholderContent.replace(/{{ APP_URL }}/g, appUrl))
          } catch (e) {
            resolvedConfig.logger.error(`Error serving placeholder index.html: ${e instanceof Error ? e.message : e}`)
            res.statusCode = 404
            res.end("Not Found (Error loading placeholder)")
          }
          return
        }

        const indexPath = await findIndexHtmlPath(server, pluginConfig)

        // Serve index.html at root "/" even when base is "/static/"
        // This prevents Vite from redirecting "/" to "/static/"
        if (indexPath) {
          try {
            const htmlContent = await fs.promises.readFile(indexPath, "utf-8")
            // Transform the HTML using Vite's pipeline - this injects the correct base-prefixed paths
            const transformedHtml = await server.transformIndexHtml(requestUrl, htmlContent, requestUrl)
            res.statusCode = 200
            res.setHeader("Content-Type", "text/html")
            res.end(transformedHtml)
            return
          } catch (e) {
            const relIndexPath = path.relative(server.config.root, indexPath)
            resolvedConfig.logger.error(`Error serving index.html from ${relIndexPath}: ${e instanceof Error ? e.message : e}`)
            next(e)
            return
          }
        }

        // Serve placeholder for "/" or "/index.html" when no index.html exists
        // This is useful for modes where there's no index.html at all
        try {
          const placeholderPath = path.join(dirname(), "dev-server-index.html")
          const placeholderContent = await fs.promises.readFile(placeholderPath, "utf-8")
          res.statusCode = 200
          res.setHeader("Content-Type", "text/html")
          res.end(placeholderContent.replace(/{{ APP_URL }}/g, appUrl))
        } catch (e) {
          resolvedConfig.logger.error(`Error serving placeholder index.html: ${e instanceof Error ? e.message : e}`)
          res.statusCode = 404
          res.end("Not Found (Error loading placeholder)")
        }
      })
    },
  }
}

/**
 * Validate the command can run in the given environment.
 */
function ensureCommandShouldRunInEnvironment(command: "build" | "serve", env: Record<string, string>, mode?: string): void {
  const allowedDevModes = ["dev", "development", "local", "docker"]
  if (command === "build" || env.LITESTAR_BYPASS_ENV_CHECK === "1") {
    return
  }

  if (mode === "test" || env.VITEST || env.VITE_TEST || env.NODE_ENV === "test") {
    return
  }

  if (typeof env.LITESTAR_MODE !== "undefined" && !allowedDevModes.includes(env.LITESTAR_MODE)) {
    throw Error("Run the Vite dev server only in development. Set LITESTAR_MODE=dev/development/local/docker or set LITESTAR_BYPASS_ENV_CHECK=1 to skip this check.")
  }

  if (typeof env.CI !== "undefined") {
    throw Error(
      "You should not run the Vite HMR server in CI environments. You should build your assets for production instead. To disable this ENV check you may set LITESTAR_BYPASS_ENV_CHECK=1",
    )
  }
}

function loadPythonDefaults(): BridgeSchema | null {
  const isTestEnv = Boolean(process.env.VITEST || process.env.VITE_TEST || process.env.NODE_ENV === "test")
  const defaults = readBridgeConfig()
  if (!defaults) {
    warnMissingRuntimeConfig("env", isTestEnv)
    return null
  }
  return defaults
}

/**
 * Format a beautiful startup warning message when .litestar.json is missing.
 * Uses unicode box drawing characters and colors for visual appeal.
 */
function formatMissingConfigWarning(): string {
  const y = colors.yellow
  const c = colors.cyan
  const d = colors.dim
  const b = colors.bold

  const lines = [
    "",
    y("╭─────────────────────────────────────────────────────────────────╮"),
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}  ${y("⚠")}  ${b("Litestar backend configuration not found")}                   ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}  The plugin couldn't find ${c(".litestar.json")} which is normally     ${y("│")}`,
    `${y("│")}  created when the Litestar backend starts.                     ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}  ${b("Quick fix")} - run one of these commands first:                  ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}    ${c("$ litestar run")}              ${d("# Start backend only")}            ${y("│")}`,
    `${y("│")}    ${c("$ litestar assets serve")}     ${d("# Start backend + Vite together")} ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}  Or manually configure the plugin in ${c("vite.config.ts")}:           ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}    ${d("litestar({")}                                                  ${y("│")}`,
    `${y("│")}    ${d('  input: ["src/main.tsx"],')}                                  ${y("│")}`,
    `${y("│")}    ${d('  assetUrl: "/static/",')}                                     ${y("│")}`,
    `${y("│")}    ${d('  bundleDir: "public",')}                                     ${y("│")}`,
    `${y("│")}    ${d("  types: false,")}                                             ${y("│")}`,
    `${y("│")}    ${d("})")}                                                          ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    `${y("│")}  Docs: ${c("https://docs.litestar.dev/vite/getting-started")}          ${y("│")}`,
    `${y("│")}                                                                 ${y("│")}`,
    y("╰─────────────────────────────────────────────────────────────────╯"),
    "",
    d("Continuing with defaults... some features may not work."),
    "",
  ]

  return lines.join("\n")
}

function warnMissingRuntimeConfig(_reason: "env" | "file", suppress: boolean): void {
  if (warnedMissingRuntimeConfig || suppress) return
  warnedMissingRuntimeConfig = true

  // eslint-disable-next-line no-console
  console.warn(formatMissingConfigWarning())
}

/**
 * Convert the users configuration into a standard structure with defaults.
 */
function resolvePluginConfig(config: string | string[] | PluginConfig): ResolvedPluginConfig {
  if (typeof config === "undefined") {
    throw new Error("litestar-vite-plugin: missing configuration.")
  }
  const pythonDefaults = loadPythonDefaults()
  const resolvedConfig = typeof config === "string" || Array.isArray(config) ? { input: config, ssr: config } : config

  if (typeof resolvedConfig.input === "undefined") {
    throw new Error('litestar-vite-plugin: missing configuration for "input".')
  }
  if (typeof resolvedConfig.resourceDir === "string") {
    resolvedConfig.resourceDir = resolvedConfig.resourceDir.trim().replace(/^\/+/, "").replace(/\/+$/, "")

    if (resolvedConfig.resourceDir === "") {
      throw new Error("litestar-vite-plugin: resourceDir must be a subdirectory. E.g. 'resources'.")
    }
  }

  if (typeof resolvedConfig.bundleDir === "string") {
    resolvedConfig.bundleDir = resolvedConfig.bundleDir.trim().replace(/^\/+/, "").replace(/\/+$/, "")

    if (resolvedConfig.bundleDir === "") {
      throw new Error("litestar-vite-plugin: bundleDir must be a subdirectory. E.g. 'public'.")
    }
  }

  if (typeof resolvedConfig.staticDir === "string") {
    resolvedConfig.staticDir = resolvedConfig.staticDir.trim().replace(/^\/+/, "").replace(/\/+$/, "")

    if (resolvedConfig.staticDir === "") {
      throw new Error("litestar-vite-plugin: staticDir must be a subdirectory. E.g. 'src/public'.")
    }
  }

  if (typeof resolvedConfig.ssrOutDir === "string") {
    resolvedConfig.ssrOutDir = resolvedConfig.ssrOutDir.trim().replace(/^\/+/, "").replace(/\/+$/, "")
  }

  if (resolvedConfig.refresh === true) {
    resolvedConfig.refresh = [{ paths: refreshPaths }]
  }

  // Resolve types configuration
  // Priority: explicit vite.config.ts > .litestar.json > hardcoded defaults
  //
  // Behavior:
  // - undefined or "auto": read from .litestar.json, disabled if not found
  // - true: use hardcoded defaults (ignore .litestar.json)
  // - false: disabled
  // - object: use explicit config (ignore .litestar.json for types)
  let typesConfig: Required<TypesConfig> | false = false
  const defaultTypesOutput = "src/generated"
  const defaultOpenapiPath = path.join(defaultTypesOutput, "openapi.json")
  const defaultRoutesPath = path.join(defaultTypesOutput, "routes.json")
  const defaultSchemasTsPath = path.join(defaultTypesOutput, "schemas.ts")
  const defaultPagePropsPath = path.join(defaultTypesOutput, "inertia-pages.json")

  if (resolvedConfig.types === false) {
    // Explicitly disabled - do nothing, typesConfig stays false
  } else if (resolvedConfig.types === true) {
    // Explicitly enabled with hardcoded defaults (ignores .litestar.json)
    typesConfig = {
      enabled: true,
      output: defaultTypesOutput,
      openapiPath: defaultOpenapiPath,
      routesPath: defaultRoutesPath,
      pagePropsPath: defaultPagePropsPath,
      schemasTsPath: defaultSchemasTsPath,
      generateZod: false,
      generateSdk: true,
      generateRoutes: true,
      generatePageProps: true,
      generateSchemas: true,
      globalRoute: false,
      debounce: DEBOUNCE_MS,
    }
  } else if (resolvedConfig.types === "auto" || typeof resolvedConfig.types === "undefined") {
    // Auto mode: read from .litestar.json if available, otherwise disabled
    if (pythonDefaults?.types) {
      typesConfig = {
        enabled: pythonDefaults.types.enabled,
        output: pythonDefaults.types.output,
        openapiPath: pythonDefaults.types.openapiPath,
        routesPath: pythonDefaults.types.routesPath,
        pagePropsPath: pythonDefaults.types.pagePropsPath,
        schemasTsPath: pythonDefaults.types.schemasTsPath ?? path.join(pythonDefaults.types.output, "schemas.ts"),
        generateZod: pythonDefaults.types.generateZod,
        generateSdk: pythonDefaults.types.generateSdk,
        generateRoutes: pythonDefaults.types.generateRoutes,
        generatePageProps: pythonDefaults.types.generatePageProps,
        generateSchemas: pythonDefaults.types.generateSchemas ?? true,
        globalRoute: pythonDefaults.types.globalRoute,
        debounce: DEBOUNCE_MS,
      }
    }
    // If no pythonDefaults, typesConfig stays false (disabled)
  } else if (typeof resolvedConfig.types === "object" && resolvedConfig.types !== null) {
    // Explicit object config - user overrides
    const userProvidedOpenapi = Object.hasOwn(resolvedConfig.types, "openapiPath")
    const userProvidedRoutes = Object.hasOwn(resolvedConfig.types, "routesPath")
    const userProvidedPageProps = Object.hasOwn(resolvedConfig.types, "pagePropsPath")
    const userProvidedSchemasTs = Object.hasOwn(resolvedConfig.types, "schemasTsPath")

    typesConfig = {
      enabled: resolvedConfig.types.enabled ?? true,
      output: resolvedConfig.types.output ?? defaultTypesOutput,
      openapiPath: resolvedConfig.types.openapiPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "openapi.json") : defaultOpenapiPath),
      routesPath: resolvedConfig.types.routesPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "routes.json") : defaultRoutesPath),
      pagePropsPath: resolvedConfig.types.pagePropsPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "inertia-pages.json") : defaultPagePropsPath),
      schemasTsPath: resolvedConfig.types.schemasTsPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "schemas.ts") : defaultSchemasTsPath),
      generateZod: resolvedConfig.types.generateZod ?? false,
      generateSdk: resolvedConfig.types.generateSdk ?? true,
      generateRoutes: resolvedConfig.types.generateRoutes ?? true,
      generatePageProps: resolvedConfig.types.generatePageProps ?? true,
      generateSchemas: resolvedConfig.types.generateSchemas ?? true,
      globalRoute: resolvedConfig.types.globalRoute ?? false,
      debounce: resolvedConfig.types.debounce ?? DEBOUNCE_MS,
    }

    // If the user only set output (not openapi/routes/pageProps), cascade them under output for consistency
    if (!userProvidedOpenapi && resolvedConfig.types.output) {
      typesConfig.openapiPath = path.join(typesConfig.output, "openapi.json")
    }
    if (!userProvidedRoutes && resolvedConfig.types.output) {
      typesConfig.routesPath = path.join(typesConfig.output, "routes.json")
    }
    if (!userProvidedPageProps && resolvedConfig.types.output) {
      typesConfig.pagePropsPath = path.join(typesConfig.output, "inertia-pages.json")
    }
    if (!userProvidedSchemasTs && resolvedConfig.types.output) {
      typesConfig.schemasTsPath = path.join(typesConfig.output, "schemas.ts")
    }
  }

  // Auto-detect Inertia mode from .litestar.json if not explicitly set
  // Check for both "hybrid" and "inertia" since Python normalizes "inertia" -> "hybrid"
  const inertiaMode = resolvedConfig.inertiaMode ?? (pythonDefaults?.mode === "hybrid" || pythonDefaults?.mode === "inertia")

  const effectiveResourceDir = resolvedConfig.resourceDir ?? pythonDefaults?.resourceDir ?? "src"
  const resolvedBundleDir = resolvedConfig.bundleDir ?? pythonDefaults?.bundleDir ?? "public"
  const resolvedStaticDir = resolvedConfig.staticDir ?? pythonDefaults?.staticDir ?? path.join(effectiveResourceDir, "public")
  const resolvedHotFile = resolvedConfig.hotFile ?? pythonDefaults?.hotFile ?? path.join(resolvedBundleDir, "hot")

  const deployAssetUrlRaw = resolvedConfig.deployAssetUrl ?? pythonDefaults?.deployAssetUrl ?? undefined

  const result: ResolvedPluginConfig = {
    input: resolvedConfig.input,
    assetUrl: normalizeAssetUrl(resolvedConfig.assetUrl ?? pythonDefaults?.assetUrl ?? "/static/"),
    deployAssetUrl: typeof deployAssetUrlRaw === "string" ? normalizeAssetUrl(deployAssetUrlRaw) : undefined,
    resourceDir: effectiveResourceDir,
    bundleDir: resolvedBundleDir,
    staticDir: resolvedStaticDir,
    ssr: resolvedConfig.ssr ?? resolvedConfig.input,
    ssrOutDir: resolvedConfig.ssrOutDir ?? pythonDefaults?.ssrOutDir ?? path.join(effectiveResourceDir, "bootstrap/ssr"),
    refresh: resolvedConfig.refresh ?? false,
    hotFile: resolvedHotFile,
    detectTls: resolvedConfig.detectTls ?? false,
    autoDetectIndex: resolvedConfig.autoDetectIndex ?? true,
    inertiaMode,
    transformOnServe: resolvedConfig.transformOnServe ?? ((code) => code),
    types: typesConfig,
    executor: resolvedConfig.executor ?? pythonDefaults?.executor,
    hasPythonConfig: pythonDefaults !== null,
  }

  // Validate config against Python defaults and warn on mismatches
  validateAgainstPythonDefaults(result, pythonDefaults, resolvedConfig)

  return result
}

/**
 * Validate resolved config against Python defaults and warn on mismatches.
 *
 * This function implements the "Smart Merge with Validation" pattern:
 * - vite.config.ts values take precedence (as they should)
 * - But we warn when they differ from Python's .litestar.json
 * - This helps catch configuration drift between Python and TypeScript
 *
 * @param resolved - The fully resolved plugin configuration
 * @param pythonDefaults - The defaults read from .litestar.json (if present)
 * @param userConfig - The original user config from vite.config.ts
 */
function validateAgainstPythonDefaults(resolved: ResolvedPluginConfig, pythonDefaults: BridgeSchema | null, userConfig: PluginConfig): void {
  if (!pythonDefaults) return

  const warnings: string[] = []

  // Only warn for fields that were explicitly set in vite.config.ts
  // AND differ from Python defaults. Don't warn when:
  // - Using Python defaults as fallback (user didn't explicitly set the value)
  // - Python defaults don't have a meaningful value for the field (null/undefined)

  // Helper to check if a Python default value is meaningful (not null/undefined)
  const hasPythonValue = (value: unknown): value is string => typeof value === "string" && value.length > 0

  // Helper to compare paths by resolving to absolute - handles "../" relative paths
  const pathsAreSame = (a: string, b: string): boolean => {
    const resolvedA = path.resolve(process.cwd(), a)
    const resolvedB = path.resolve(process.cwd(), b)
    return resolvedA === resolvedB
  }

  if (userConfig.assetUrl !== undefined && hasPythonValue(pythonDefaults.assetUrl) && resolved.assetUrl !== pythonDefaults.assetUrl) {
    warnings.push(`assetUrl: vite.config.ts="${resolved.assetUrl}" differs from Python="${pythonDefaults.assetUrl}"`)
  }

  if (userConfig.bundleDir !== undefined && hasPythonValue(pythonDefaults.bundleDir) && !pathsAreSame(resolved.bundleDir, pythonDefaults.bundleDir)) {
    warnings.push(`bundleDir: vite.config.ts="${resolved.bundleDir}" differs from Python="${pythonDefaults.bundleDir}"`)
  }

  if (userConfig.resourceDir !== undefined && hasPythonValue(pythonDefaults.resourceDir) && !pathsAreSame(resolved.resourceDir, pythonDefaults.resourceDir)) {
    warnings.push(`resourceDir: vite.config.ts="${resolved.resourceDir}" differs from Python="${pythonDefaults.resourceDir}"`)
  }

  if (userConfig.staticDir !== undefined && hasPythonValue(pythonDefaults.staticDir) && !pathsAreSame(resolved.staticDir, pythonDefaults.staticDir)) {
    warnings.push(`staticDir: vite.config.ts="${resolved.staticDir}" differs from Python="${pythonDefaults.staticDir}"`)
  }

  const frameworkMode = pythonDefaults.mode === "framework" || pythonDefaults.mode === "ssr" || pythonDefaults.mode === "ssg"
  if (frameworkMode && userConfig.ssrOutDir !== undefined && hasPythonValue(pythonDefaults.ssrOutDir) && !pathsAreSame(resolved.ssrOutDir, pythonDefaults.ssrOutDir)) {
    warnings.push(`ssrOutDir: vite.config.ts="${resolved.ssrOutDir}" differs from Python="${pythonDefaults.ssrOutDir}"`)
  }

  if (warnings.length > 0) {
    // eslint-disable-next-line no-console
    console.warn(
      colors.yellow("[litestar-vite] Configuration mismatch detected:\n") +
        warnings.map((w) => `  ${colors.dim("•")} ${w}`).join("\n") +
        `\n\n${colors.dim("Precedence: vite.config.ts > .litestar.json > defaults")}\n` +
        colors.dim("See: https://docs.litestar.dev/vite/config-precedence\n"),
    )
  }
}

/**
 * Resolve the Vite base option from the configuration.
 */
function resolveBase(_config: ResolvedPluginConfig, assetUrl: string): string {
  // In development mode, use the assetUrl directly
  if (process.env.NODE_ENV === "development") {
    return assetUrl
  }
  // In production, use the full assetUrl
  return assetUrl.endsWith("/") ? assetUrl : `${assetUrl}/`
}

/**
 * Resolve the Vite input path from the configuration.
 */
function resolveInput(config: ResolvedPluginConfig, ssr: boolean): string | string[] | undefined {
  if (ssr) {
    return config.ssr
  }

  return config.input
}

/**
 * Check if a path is absolute (Unix or Windows).
 */
function isAbsolutePath(path: string): boolean {
  // Unix absolute path starts with /
  // Windows absolute path starts with drive letter (C:\, D:\, etc.)
  return path.startsWith("/") || /^[a-zA-Z]:[\\/]/.test(path)
}

/**
 * Resolve the Vite outDir path from the configuration.
 *
 * For relative paths: strips leading slashes (legacy behavior for Vite resolution).
 * For absolute paths: preserves the path, only strips trailing slashes.
 *
 * This ensures absolute paths like `/home/user/project/public` work correctly
 * instead of being converted to `home/user/project/public`.
 */
function resolveOutDir(config: ResolvedPluginConfig, ssr: boolean): string {
  const dir = ssr ? config.ssrOutDir : config.bundleDir

  // Preserve absolute paths (Unix or Windows)
  if (isAbsolutePath(dir)) {
    return dir.replace(/[\\/]+$/, "") // Only strip trailing slashes
  }

  // For relative paths, strip leading slashes (legacy behavior)
  return dir.replace(/^\/+/, "").replace(/\/+$/, "")
}

function resolveFullReloadConfig({ refresh: config }: ResolvedPluginConfig): PluginOption[] {
  if (typeof config === "boolean") {
    return []
  }

  if (typeof config === "string") {
    config = [{ paths: [config] }]
  }

  if (!Array.isArray(config)) {
    config = [config]
  }

  if (config.some((c) => typeof c === "string")) {
    config = [{ paths: config }] as RefreshConfig[]
  }

  return (config as RefreshConfig[]).flatMap((c) => {
    const plugin = fullReload(c.paths, c.config)

    /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
    /** @ts-ignore */
    plugin.__litestar_plugin_config = c

    return plugin
  })
}

/**
 * Resolve the dev server URL from the server address and configuration.
 */
function resolveDevServerUrl(address: AddressInfo, config: ResolvedConfig, userConfig: UserConfig): DevServerUrl {
  const configHmrProtocol = typeof config.server.hmr === "object" ? config.server.hmr.protocol : null
  const clientProtocol = configHmrProtocol ? (configHmrProtocol === "wss" ? "https" : "http") : null
  const serverProtocol = config.server.https ? "https" : "http"
  const protocol = clientProtocol ?? serverProtocol

  const configHmrHost = typeof config.server.hmr === "object" ? config.server.hmr.host : null
  const configHost = typeof config.server.host === "string" ? config.server.host : null
  const remoteHost = process.env.VITE_ALLOW_REMOTE && !userConfig.server?.host ? "localhost" : null
  const serverAddress = isIpv6(address) ? `[${address.address}]` : address.address
  let host = configHmrHost ?? remoteHost ?? configHost ?? serverAddress

  // Normalize 0.0.0.0 to 127.0.0.1 - 0.0.0.0 is a bind address meaning "all interfaces"
  // but is not connectable as a target address for the proxy
  if (host === "0.0.0.0") {
    host = "127.0.0.1"
  }

  const configHmrClientPort = typeof config.server.hmr === "object" ? config.server.hmr.clientPort : null
  const port = configHmrClientPort ?? address.port

  return `${protocol}://${host}:${port}`
}

function isIpv6(address: AddressInfo): boolean {
  return (
    address.family === "IPv6" ||
    // In node >=18.0 <18.4 this was an integer value. This was changed in a minor version.
    // See: https://github.com/laravel/vite-plugin/issues/103
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore-next-line
    address.family === 6
  )
}

/**
 * Add the Inertia helpers to the list of SSR dependencies that aren't externalized.
 *
 * @see https://vitejs.dev/guide/ssr.html#ssr-externals
 */
function noExternalInertiaHelpers(config: UserConfig): true | Array<string | RegExp> {
  /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
  /* @ts-ignore */
  const userNoExternal = (config.ssr as SSROptions | undefined)?.noExternal
  const pluginNoExternal = ["litestar-vite-plugin"]

  if (userNoExternal === true) {
    return true
  }

  if (typeof userNoExternal === "undefined") {
    return pluginNoExternal
  }

  return [...(Array.isArray(userNoExternal) ? userNoExternal : [userNoExternal]), ...pluginNoExternal]
}

/**
 * Resolve the server config from the environment.
 */
function resolveEnvironmentServerConfig(env: Record<string, string>):
  | {
      hmr?: { host: string }
      host?: string
      https?: { cert: Buffer; key: Buffer }
    }
  | undefined {
  if (!env.VITE_SERVER_KEY && !env.VITE_SERVER_CERT) {
    return
  }

  if (!fs.existsSync(env.VITE_SERVER_KEY) || !fs.existsSync(env.VITE_SERVER_CERT)) {
    throw Error(
      `Unable to find the certificate files specified in your environment. Ensure you have correctly configured VITE_SERVER_KEY: [${env.VITE_SERVER_KEY}] and VITE_SERVER_CERT: [${env.VITE_SERVER_CERT}].`,
    )
  }

  const host = resolveHostFromEnv(env)

  if (!host) {
    throw Error(`Unable to determine the host from the environment's APP_URL: [${env.APP_URL}].`)
  }

  return {
    hmr: { host },
    host,
    https: {
      key: fs.readFileSync(env.VITE_DEV_SERVER_KEY),
      cert: fs.readFileSync(env.VITE_DEV_SERVER_CERT),
    },
  }
}

/**
 * Resolve the host name from the environment.
 */
function resolveHostFromEnv(env: Record<string, string>): string | undefined {
  try {
    return new URL(env.APP_URL).host
  } catch {
    return
  }
}

/**
 * Resolve the Herd or Valet server config for the given host.
 */
function resolveDevelopmentEnvironmentServerConfig(host: string | boolean | null):
  | {
      hmr?: { host: string }
      host?: string
      https?: { cert: string; key: string }
    }
  | undefined {
  if (host === false) {
    return
  }

  const configPath = determineDevelopmentEnvironmentConfigPath()

  if (typeof configPath === "undefined" && host === null) {
    return
  }

  if (typeof configPath === "undefined") {
    throw Error("Unable to find the Herd or Valet configuration directory. Please check they are correctly installed.")
  }

  const resolvedHost = host === true || host === null ? `${path.basename(process.cwd())}.${resolveDevelopmentEnvironmentTld(configPath)}` : host

  const keyPath = path.resolve(configPath, "certs", `${resolvedHost}.key`)
  const certPath = path.resolve(configPath, "certs", `${resolvedHost}.crt`)

  if ((!fs.existsSync(keyPath) || !fs.existsSync(certPath)) && host === null) {
    throw Error(`Unable to find certificate files for your host [${host}] in the [${configPath}/certs] directory.`)
  }

  return {
    hmr: { host: resolvedHost },
    host: resolvedHost,
    https: {
      key: keyPath,
      cert: certPath,
    },
  }
}

/**
 * Resolve the path configuration directory.
 */
function determineDevelopmentEnvironmentConfigPath(): string | undefined {
  const envConfigPath = path.resolve(process.cwd(), ".config")

  if (fs.existsSync(envConfigPath)) {
    return envConfigPath
  }

  return path.resolve(process.cwd(), ".config")
}

/**
 * Resolve the TLD via the config path.
 */
function resolveDevelopmentEnvironmentTld(configPath: string): string {
  const configFile = path.resolve(configPath, "config.json")

  if (!fs.existsSync(configFile)) {
    throw Error(`Unable to find the configuration file [${configFile}].`)
  }

  const config: { tld: string } = JSON.parse(fs.readFileSync(configFile, "utf-8"))

  return config.tld
}

/**
 * The directory of the current file.
 */
function dirname(): string {
  // Use path.resolve relative to process.cwd() as a more robust alternative
  // Assumes the script runs from the project root or similar predictable location.
  // Adjust the relative path if necessary based on actual execution context.
  try {
    // Attempt original method first
    return fileURLToPath(new URL(".", import.meta.url))
  } catch {
    // Fallback for environments where import.meta.url is problematic (like some test runners)
    // Use dist/js since that's where built assets (including dev-server-index.html) live
    return path.resolve(process.cwd(), "dist/js")
  }
}

function normalizeAssetUrl(url: string): string {
  const trimmed = url.trim()

  if (trimmed === "") {
    return "static"
  }

  const isExternal = trimmed.startsWith("http://") || trimmed.startsWith("https://")
  if (isExternal) {
    return trimmed.replace(/\/+$/, "")
  }

  const withLeading = trimmed.startsWith("/") ? `/${trimmed.replace(/^\/+/, "")}` : trimmed
  const withTrailing = withLeading.endsWith("/") ? withLeading : `${withLeading}/`
  return withTrailing
}
