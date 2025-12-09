/**
 * Shared type generation Vite plugin.
 *
 * Creates a Vite plugin that watches for OpenAPI schema and route metadata changes
 * and regenerates TypeScript types using @hey-api/openapi-ts.
 * Used by Astro, Nuxt, and SvelteKit integrations.
 *
 * @module
 */

import { exec } from "node:child_process"
import * as fs from "node:fs"
import * as path from "node:path"
import { promisify } from "node:util"
import colors from "picocolors"
import type { Plugin, ViteDevServer } from "vite"
import { resolveInstallHint, resolvePackageExecutor } from "../install-hint.js"
import { debounce } from "./debounce.js"
import { emitRouteTypes } from "./emit-route-types.js"

const execAsync = promisify(exec)

/**
 * Base configuration for type generation.
 */
export interface BaseTypesConfig {
  /**
   * Enable type generation.
   * @default false
   */
  enabled?: boolean

  /**
   * Path to output generated TypeScript types.
   */
  output?: string

  /**
   * Path where the OpenAPI schema is exported by Litestar.
   * @default 'openapi.json'
   */
  openapiPath?: string

  /**
   * Path where route metadata is exported by Litestar.
   * @default 'routes.json'
   */
  routesPath?: string

  /**
   * Generate Zod schemas in addition to TypeScript types.
   * @default false
   */
  generateZod?: boolean

  /**
   * Generate SDK client functions for API calls.
   * @default true
   */
  generateSdk?: boolean

  /**
   * Debounce time in milliseconds for type regeneration.
   * @default 300
   */
  debounce?: number
}

/**
 * Required version of types config (all fields defined).
 */
export interface RequiredTypesConfig {
  enabled: boolean
  output: string
  openapiPath: string
  routesPath: string
  generateZod: boolean
  generateSdk: boolean
  debounce: number
}

/**
 * Options for creating the type generation plugin.
 */
export interface TypeGenPluginOptions {
  /**
   * Framework name for logging (e.g., "litestar-astro", "litestar-nuxt").
   */
  frameworkName: string

  /**
   * Vite plugin name.
   */
  pluginName: string

  /**
   * The @hey-api client plugin to use when generating SDK.
   * @default '@hey-api/client-fetch'
   */
  clientPlugin?: string

  /**
   * Optional executor for running npx/bunx/pnpm dlx commands.
   */
  executor?: string
}

/**
 * Create a Vite plugin for type generation from OpenAPI schemas.
 *
 * @param typesConfig - The type generation configuration
 * @param options - Plugin creation options
 * @returns A Vite plugin that watches for schema changes and regenerates types
 *
 * @example
 * ```typescript
 * const plugin = createTypeGenerationPlugin(
 *   { enabled: true, output: 'src/generated' },
 *   { frameworkName: 'litestar-astro', pluginName: 'litestar-astro-types' }
 * )
 * ```
 */
export function createTypeGenerationPlugin(typesConfig: RequiredTypesConfig, options: TypeGenPluginOptions): Plugin {
  const { frameworkName, pluginName, clientPlugin = "@hey-api/client-fetch", executor } = options

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
        console.log(colors.cyan(`[${frameworkName}]`), colors.yellow("OpenAPI schema not found:"), typesConfig.openapiPath)
        return false
      }

      console.log(colors.cyan(`[${frameworkName}]`), colors.dim("Generating TypeScript types..."))

      // Check for user config file first
      const projectRoot = process.cwd()
      const candidates = [path.resolve(projectRoot, "openapi-ts.config.ts"), path.resolve(projectRoot, "hey-api.config.ts"), path.resolve(projectRoot, ".hey-api.config.ts")]
      const configPath = candidates.find((p) => fs.existsSync(p)) || null

      let args: string[]
      if (configPath) {
        // Use user config file
        console.log(colors.cyan(`[${frameworkName}]`), colors.dim("Using config:"), configPath)
        args = ["@hey-api/openapi-ts", "--file", configPath]
      } else {
        // Build args with proper plugins
        args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

        const plugins = ["@hey-api/typescript", "@hey-api/schemas"]
        if (typesConfig.generateSdk) {
          plugins.push("@hey-api/sdk", clientPlugin)
        }
        if (typesConfig.generateZod) {
          plugins.push("zod")
        }
        if (plugins.length) {
          args.push("--plugins", ...plugins)
        }
      }

      // Execute the command using the appropriate executor
      const command = executor ? resolvePackageExecutor(args.join(" "), executor) : `npx ${args.join(" ")}`
      await execAsync(command, { cwd: projectRoot })

      // Also generate route types if routes.json exists
      const routesPath = path.resolve(process.cwd(), typesConfig.routesPath)
      if (fs.existsSync(routesPath)) {
        await emitRouteTypes(routesPath, typesConfig.output, { declareGlobalVars: true })
      }

      const duration = Date.now() - startTime
      console.log(colors.cyan(`[${frameworkName}]`), colors.green("Types generated"), colors.dim(`in ${duration}ms`))

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
        console.log(colors.cyan(`[${frameworkName}]`), colors.yellow("@hey-api/openapi-ts not installed"), "- run:", resolveInstallHint())
      } else {
        console.error(colors.cyan(`[${frameworkName}]`), colors.red("Type generation failed:"), message)
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

  return {
    name: pluginName,
    enforce: "pre",

    configureServer(devServer) {
      server = devServer
      console.log(colors.cyan(`[${frameworkName}]`), colors.dim("Watching for schema changes:"), colors.yellow(typesConfig.openapiPath))
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
        console.log(colors.cyan(`[${frameworkName}]`), colors.dim("Schema changed:"), colors.yellow(relativePath))
        debouncedRunTypeGeneration()
      }
    },
  }
}
