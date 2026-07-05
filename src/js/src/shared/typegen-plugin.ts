/**
 * Unified Litestar type generation Vite plugin.
 *
 * This is a thin wrapper around typegen-core.ts that adds:
 * - Vite plugin lifecycle hooks
 * - File watching with debounce
 * - Caching for HMR efficiency
 * - WebSocket notifications
 */
import fs from "node:fs"
import path from "node:path"
import colors from "picocolors"
import type { Plugin, ResolvedConfig, ViteDevServer } from "vite"

import { debounce } from "./debounce.js"
import { shouldRegeneratePageProps, shouldRunOpenApiTs, updateOpenApiTsCache, updatePagePropsCache } from "./typegen-cache.js"
import { runTypeGeneration, type TypeGenCoreConfig, type TypeGenLogger, type TypeGenResult } from "./typegen-core.js"

export interface RequiredTypeGenConfig {
  enabled: boolean
  output: string
  openapiPath: string
  routesPath: string
  pagePropsPath: string
  schemasTsPath?: string
  generateZod: boolean
  generateSdk: boolean
  generateRoutes: boolean
  generatePageProps: boolean
  generateSchemas: boolean
  globalRoute: boolean
  failOnError?: boolean
  debounce: number
}

export interface TypeGenPluginOptions {
  /** Vite plugin name */
  pluginName: string
  /** Human-friendly prefix for logs */
  frameworkName: string
  /** @hey-api client plugin (e.g. "@hey-api/client-axios") */
  sdkClientPlugin: string
  /** JS runtime executor for package commands */
  executor?: string
  /** Whether .litestar.json was present (used for buildStart warnings) */
  hasPythonConfig?: boolean
}

async function getFileMtime(filePath: string): Promise<string> {
  const stat = await fs.promises.stat(filePath)
  return stat.mtimeMs.toString()
}

/**
 * Unified Litestar type generation Vite plugin.
 *
 * Watches OpenAPI, routes.json, and inertia page props metadata and generates:
 * - API types via @hey-api/openapi-ts (optional)
 * - routes.ts (optional)
 * - page-props.ts (optional)
 */
export function createLitestarTypeGenPlugin(typesConfig: RequiredTypeGenConfig, options: TypeGenPluginOptions): Plugin {
  const { pluginName, frameworkName, sdkClientPlugin, executor, hasPythonConfig } = options

  let lastTypesHash: string | null = null
  let lastPagePropsHash: string | null = null
  let lastRoutesHash: string | null = null
  let server: ViteDevServer | null = null
  let generationPromise: Promise<TypeGenResult> | null = null
  let rerunRequested = false
  let resolvedConfig: ResolvedConfig | null = null

  /**
   * Create a logger that uses Vite's logger.
   */
  function createViteLogger(): TypeGenLogger {
    return {
      info: (message: string) => resolvedConfig?.logger.info(`${colors.cyan("•")} ${message}`),
      warn: (message: string) => resolvedConfig?.logger.warn(`${colors.yellow("!")} ${message}`),
      error: (message: string) => resolvedConfig?.logger.error(`${colors.red("✗")} ${message}`),
    }
  }

  /**
   * Run type generation with caching for HMR efficiency.
   */
  async function runTypeGenerationWithCache(): Promise<TypeGenResult> {
    if (generationPromise) {
      rerunRequested = true
      return generationPromise
    }

    generationPromise = (async () => {
      const combined: TypeGenResult = {
        generated: false,
        generatedFiles: [],
        skippedFiles: [],
        durationMs: 0,
        warnings: [],
        errors: [],
      }
      const projectRoot = resolvedConfig?.root ?? process.cwd()
      const logger = createViteLogger()
      const cache = {
        shouldRunOpenApiTs,
        updateOpenApiTsCache,
        shouldRegeneratePageProps,
        updatePagePropsCache,
      }

      try {
        do {
          rerunRequested = false
          const startTime = Date.now()
          const coreConfig: TypeGenCoreConfig = {
            projectRoot,
            openapiPath: typesConfig.openapiPath,
            output: typesConfig.output,
            routesPath: typesConfig.routesPath,
            pagePropsPath: typesConfig.pagePropsPath,
            generateSdk: typesConfig.generateSdk,
            generateZod: typesConfig.generateZod,
            generatePageProps: typesConfig.generatePageProps,
            generateSchemas: typesConfig.generateSchemas,
            schemasTsPath: typesConfig.schemasTsPath,
            sdkClientPlugin,
            executor,
          }

          const result = await runTypeGeneration(coreConfig, { logger, cache })
          combined.generated ||= result.generated
          combined.generatedFiles.push(...result.generatedFiles)
          combined.skippedFiles.push(...result.skippedFiles)
          combined.warnings.push(...result.warnings)
          combined.errors.push(...result.errors)
          combined.durationMs += result.durationMs || Date.now() - startTime

          for (const file of result.skippedFiles) {
            const label = file.endsWith("page-props.ts") ? "Page props types" : file.endsWith("schemas.ts") ? "Schema types" : file.includes("api") ? "TypeScript types" : file
            resolvedConfig?.logger.info(`${colors.cyan("•")} ${label} ${colors.dim("(unchanged)")}`)
          }
        } while (rerunRequested)

        if (combined.generated && resolvedConfig) {
          resolvedConfig.logger.info(`${colors.green("✓")} TypeScript artifacts updated ${colors.dim(`(${combined.durationMs}ms)`)}`)
        }

        if (combined.generated && server) {
          server.ws.send({
            type: "custom",
            event: "litestar:types-updated",
            data: {
              output: typesConfig.output,
              timestamp: Date.now(),
            },
          })
        }

        return combined
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        resolvedConfig?.logger.error(`${colors.cyan("litestar-vite")} ${colors.red("type generation failed:")} ${message}`)
        combined.errors.push(message)
        return combined
      } finally {
        generationPromise = null
      }
    })()

    return generationPromise
  }

  const debouncedRunTypeGeneration = debounce(async (file: string, cacheKey: "openapi" | "pageProps" | "routes") => {
    const newHash = await getFileMtime(file)
    if (cacheKey === "openapi" && lastTypesHash === newHash) return
    if (cacheKey === "pageProps" && lastPagePropsHash === newHash) return
    if (cacheKey === "routes" && lastRoutesHash === newHash) return

    const result = await runTypeGenerationWithCache()
    if (result.errors.length === 0) {
      if (cacheKey === "openapi") lastTypesHash = newHash
      if (cacheKey === "pageProps") lastPagePropsHash = newHash
      if (cacheKey === "routes") lastRoutesHash = newHash
    }
  }, typesConfig.debounce)

  function shouldFailOnTypegenError(): boolean {
    return typesConfig.failOnError ?? resolvedConfig?.command === "build"
  }

  function reportTypegenErrors(result: TypeGenResult, context: { error(message: string): void; warn(message: string): void }): void {
    if (!result.errors.length) {
      return
    }

    const message = `Litestar type generation failed:\n${result.errors.join("\n")}`
    if (shouldFailOnTypegenError()) {
      context.error(message)
    } else {
      context.warn(message)
    }
  }

  return {
    name: pluginName,
    enforce: "pre",

    configResolved(config) {
      resolvedConfig = config
    },

    configureServer(devServer) {
      server = devServer
      if (typesConfig.enabled) {
        const openapiRel = path.basename(typesConfig.openapiPath)
        resolvedConfig?.logger.info(`${colors.cyan("•")} Watching: ${colors.yellow(openapiRel)}`)
      }
    },

    async buildStart() {
      if (typesConfig.enabled && hasPythonConfig === false) {
        const projectRoot = resolvedConfig?.root ?? process.cwd()
        const openapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
        if (!fs.existsSync(openapiPath)) {
          this.warn(
            "Type generation is enabled but .litestar.json was not found.\n" +
              "The Litestar backend generates this file on startup.\n\n" +
              "Solutions:\n" +
              `  1. Start the backend first: ${colors.cyan("litestar run")}\n` +
              `  2. Use integrated dev: ${colors.cyan("litestar assets serve")}\n` +
              `  3. Disable types: ${colors.cyan("litestar({ input: [...], types: false })")}\n`,
          )
        }
      }

      if (typesConfig.enabled) {
        const projectRoot = resolvedConfig?.root ?? process.cwd()
        const openapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
        const pagePropsPath = path.resolve(projectRoot, typesConfig.pagePropsPath)
        const routesPath = path.resolve(projectRoot, typesConfig.routesPath)
        const hasOpenapi = fs.existsSync(openapiPath)
        const hasPageProps = typesConfig.generatePageProps && fs.existsSync(pagePropsPath)
        const hasRoutes = typesConfig.generateSchemas && fs.existsSync(routesPath)
        if (hasOpenapi || hasPageProps || hasRoutes) {
          const result = await runTypeGenerationWithCache()
          reportTypegenErrors(result, this)
        }
      }
    },

    async handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const root = resolvedConfig?.root ?? process.cwd()
      const absoluteFile = path.resolve(file)
      const relativePath = path.relative(root, absoluteFile)
      const openapiPath = path.resolve(root, typesConfig.openapiPath)
      const pagePropsPath = path.resolve(root, typesConfig.pagePropsPath)
      const routesPath = path.resolve(root, typesConfig.routesPath)

      const isOpenapi = absoluteFile === openapiPath
      const isPageProps = typesConfig.generatePageProps && absoluteFile === pagePropsPath
      const isRoutes = typesConfig.generateSchemas && absoluteFile === routesPath

      if (isOpenapi || isPageProps || isRoutes) {
        resolvedConfig?.logger.info(`${colors.cyan(frameworkName)} ${colors.dim("schema changed:")} ${colors.yellow(relativePath)}`)
        debouncedRunTypeGeneration(absoluteFile, isOpenapi ? "openapi" : isPageProps ? "pageProps" : "routes")
      }
    },
  }
}
