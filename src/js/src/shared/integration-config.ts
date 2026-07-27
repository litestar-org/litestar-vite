/**
 * Shared configuration contract for the framework integrations.
 *
 * `astro.ts`, `nuxt.ts`, and `sveltekit.ts` each expose a `litestar()` integration whose
 * user-facing options and bridge-file resolution are identical -- only the default type-output
 * directory differs. This module owns that single implementation so the integrations cannot
 * drift apart.
 */
import { type BridgeTypesConfig, readBridgeConfig } from "./bridge-schema.js"
import { resolveHotFilePath, resolveLitestarPort } from "./network.js"
import { type RequiredTypeGenConfig, resolveTypesConfig, type TypesConfigShape } from "./typegen-plugin.js"

/** JavaScript runtime used to invoke package commands. */
type IntegrationExecutor = "node" | "bun" | "deno" | "yarn" | "pnpm"

/** Proxy strategy reported by the Python side in `.litestar.json`. */
type IntegrationProxyMode = "vite" | "direct" | "proxy" | null

/**
 * User-facing options accepted by every framework integration.
 */
export interface LitestarIntegrationConfig {
  /**
   * Litestar backend URL that API requests are proxied to.
   *
   * @default 'http://localhost:8000'
   */
  apiProxy?: string
  /**
   * Path prefix treated as backend API routes.
   *
   * @default '/api'
   */
  apiPrefix?: string
  /**
   * Type generation. `true` enables with defaults, `false` disables, or pass an object
   * to override individual fields.
   *
   * @default false
   */
  types?: boolean | "auto" | TypesConfigShape
  /**
   * Log integration activity.
   *
   * @default false
   */
  verbose?: boolean
  /**
   * JavaScript runtime executor for package commands. Overrides the executor reported by
   * Python in `.litestar.json`.
   */
  executor?: IntegrationExecutor
}

/**
 * Integration configuration with defaults applied and bridge-file values merged in.
 */
export interface ResolvedIntegrationConfig {
  apiProxy: string
  apiPrefix: string
  types: RequiredTypeGenConfig | false
  verbose: boolean
  hotFile?: string
  proxyMode: IntegrationProxyMode
  /** Preferred dev server port (provided by Python via `VITE_PORT` or the bridge file). */
  port?: number
  /**
   * Litestar dev server port. Used to set `vite.server.ws.clientPort` on Vite
   * 8.1+ (`vite.server.hmr.clientPort` on Vite 7 / 8.0) so the browser opens HMR
   * WebSockets against Litestar (single-port contract).
   */
  litestarPort?: number
  /** Asset URL prefix (e.g. `/static`); used to build the HMR path. */
  assetUrl?: string
  /** JavaScript runtime executor for package commands. */
  executor?: IntegrationExecutor
  /** Whether `.litestar.json` was found. */
  hasPythonConfig: boolean
}

function resolvePortFromEnv(): number | undefined {
  const envPort = process.env.VITE_PORT
  if (!envPort) {
    return undefined
  }
  const parsed = Number.parseInt(envPort, 10)
  return Number.isNaN(parsed) ? undefined : parsed
}

/**
 * Apply defaults and merge `.litestar.json` values into a framework integration's options.
 *
 * @param config - User-supplied integration options.
 * @param defaultOutput - Framework-conventional directory for generated types, used when the
 *   user and Python side both leave `types.output` unset.
 * @returns The resolved configuration.
 */
export function resolveIntegrationConfig(config: LitestarIntegrationConfig, defaultOutput: string): ResolvedIntegrationConfig {
  let hotFile: string | undefined
  let proxyMode: IntegrationProxyMode = "vite"
  let port = resolvePortFromEnv()
  let pythonTypesConfig: BridgeTypesConfig | undefined
  let pythonExecutor: IntegrationExecutor | undefined
  let assetUrl: string | undefined
  let litestarPort: number | undefined
  let hasPythonConfig = false

  const runtime = readBridgeConfig()
  if (runtime) {
    hasPythonConfig = true
    hotFile = resolveHotFilePath(runtime.bundleDir, runtime.hotFile)
    proxyMode = runtime.proxyMode
    port = runtime.port
    pythonExecutor = runtime.executor
    assetUrl = runtime.assetUrl
    if (runtime.types) {
      pythonTypesConfig = runtime.types
    }
  }

  const resolvedLitestarPort = resolveLitestarPort(runtime?.litestarPort, runtime?.appUrl)
  if (resolvedLitestarPort !== null) {
    litestarPort = resolvedLitestarPort
  }

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    types: resolveTypesConfig({
      requested: config.types,
      pythonConfig: pythonTypesConfig ?? undefined,
      defaultOutput,
      mergePythonWhenTrue: true,
      mergePythonForObject: true,
    }),
    verbose: config.verbose ?? false,
    hotFile,
    proxyMode,
    port,
    litestarPort,
    assetUrl,
    executor: config.executor ?? pythonExecutor,
    hasPythonConfig,
  }
}
