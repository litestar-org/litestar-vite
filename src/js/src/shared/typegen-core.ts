/**
 * Core type generation logic shared between CLI and Vite plugin.
 *
 * This module contains the pure business logic for type generation,
 * decoupled from execution context (CLI vs Vite plugin).
 *
 * Design principles:
 * - Context-agnostic: No Vite-specific imports
 * - Explicit inputs: All paths and config passed as parameters
 * - Structured output: Returns results for callers to handle
 * - Caching optional: Caller decides whether to use caching
 */
import { exec } from "node:child_process"
import fs from "node:fs"
import { createRequire } from "node:module"
import path from "node:path"
import { promisify } from "node:util"

import { resolveInstallHint, resolvePackageExecutor } from "../install-hint.js"
import { emitPagePropsTypes } from "./emit-page-props-types.js"
import { emitSchemasTypes } from "./emit-schemas-types.js"

const execAsync = promisify(exec)
const nodeRequire = createRequire(import.meta.url)

/**
 * Configuration for type generation.
 */
export interface TypeGenCoreConfig {
  /** Project root directory */
  projectRoot: string
  /** Path to openapi.json (relative or absolute) */
  openapiPath: string
  /** Output directory for generated files */
  output: string
  /** Path to inertia-pages.json (relative or absolute) */
  pagePropsPath: string
  /** Path to routes.json (relative or absolute) */
  routesPath: string
  /** Whether to generate SDK client */
  generateSdk: boolean
  /** Whether to generate Zod schemas */
  generateZod: boolean
  /** Whether to generate page props types */
  generatePageProps: boolean
  /** Whether to generate schema helper types (schemas.ts) */
  generateSchemas: boolean
  /** Optional path for schemas.ts output */
  schemasTsPath?: string
  /** SDK client plugin (e.g., "@hey-api/client-fetch") */
  sdkClientPlugin: string
  /** JS runtime executor (e.g., "bun", "pnpm") */
  executor?: string
}

/**
 * Result of type generation.
 */
export interface TypeGenResult {
  /** Whether any files were generated */
  generated: boolean
  /** Files that were generated/updated */
  generatedFiles: string[]
  /** Files that were skipped (unchanged) */
  skippedFiles: string[]
  /** Total duration in milliseconds */
  durationMs: number
  /** Any warnings to report */
  warnings: string[]
  /** Any errors encountered */
  errors: string[]
}

/**
 * Logger interface for type generation.
 * Allows callers to inject their own logging behavior.
 */
export interface TypeGenLogger {
  info(message: string): void
  warn(message: string): void
  error(message: string): void
}

/**
 * Options for running type generation.
 */
export interface RunTypeGenOptions {
  /** Logger for output (optional - silent if not provided) */
  logger?: TypeGenLogger
}

/**
 * Find user's openapi-ts config file.
 */
export function findOpenApiTsConfig(projectRoot: string): string | null {
  const candidates = [path.resolve(projectRoot, "openapi-ts.config.ts"), path.resolve(projectRoot, "hey-api.config.ts"), path.resolve(projectRoot, ".hey-api.config.ts")]
  return candidates.find((p) => fs.existsSync(p)) || null
}

/**
 * Build the list of plugins for @hey-api/openapi-ts.
 */
export function buildHeyApiPlugins(config: { generateSdk: boolean; generateZod: boolean; sdkClientPlugin: string }): string[] {
  const plugins = ["@hey-api/typescript", "@hey-api/schemas"]
  if (config.generateSdk) {
    plugins.push("@hey-api/sdk", config.sdkClientPlugin)
  }
  if (config.generateZod) {
    plugins.push("zod")
  }
  return plugins
}

/**
 * Run @hey-api/openapi-ts to generate TypeScript types from OpenAPI spec.
 *
 * @param config - Type generation configuration
 * @param configPath - Path to user's openapi-ts config (or null for default)
 * @param plugins - List of plugins to use
 * @param logger - Optional logger for output
 * @returns Path to output directory
 */
export async function runHeyApiGeneration(config: TypeGenCoreConfig, configPath: string | null, plugins: string[], logger?: TypeGenLogger): Promise<string> {
  const { projectRoot, openapiPath, output, executor, generateZod } = config

  // openapi-ts clears its output directory, so we isolate it from our own artifacts
  const sdkOutput = path.join(output, "api")

  if (process.env.VITEST || process.env.VITE_TEST || process.env.NODE_ENV === "test" || process.env.CI) {
    try {
      nodeRequire.resolve("@hey-api/openapi-ts/package.json", { paths: [projectRoot] })
    } catch {
      throw new Error("@hey-api/openapi-ts not installed")
    }
  }

  let args: string[]
  if (configPath) {
    args = ["@hey-api/openapi-ts", "--file", configPath]
  } else {
    // Use relative path for -i to match what user would type
    const relativeOpenapiPath = path.relative(projectRoot, path.resolve(projectRoot, openapiPath))
    args = ["@hey-api/openapi-ts", "-i", relativeOpenapiPath, "-o", sdkOutput]
    if (plugins.length) {
      args.push("--plugins", ...plugins)
    }
  }

  // Check for zod dependency
  if (generateZod) {
    try {
      nodeRequire.resolve("zod", { paths: [projectRoot] })
    } catch {
      logger?.warn(`zod not installed - run: ${resolveInstallHint()} zod`)
    }
  }

  const cmd = resolvePackageExecutor(args.join(" "), executor)
  await execAsync(cmd, { cwd: projectRoot })

  return sdkOutput
}

/**
 * Run the complete type generation pipeline.
 *
 * This is the main entry point for type generation, handling:
 * - OpenAPI type generation via @hey-api/openapi-ts
 * - Page props type generation
 *
 * @param config - Type generation configuration
 * @param options - Runtime options (logger, etc.)
 * @returns Result with generated files and timing info
 */
export async function runTypeGeneration(config: TypeGenCoreConfig, options: RunTypeGenOptions = {}): Promise<TypeGenResult> {
  const { logger } = options
  const startTime = Date.now()

  const result: TypeGenResult = {
    generated: false,
    generatedFiles: [],
    skippedFiles: [],
    durationMs: 0,
    warnings: [],
    errors: [],
  }

  try {
    const { projectRoot, openapiPath, pagePropsPath, output, generateSdk, generatePageProps } = config

    const absoluteOpenapiPath = path.resolve(projectRoot, openapiPath)
    const absolutePagePropsPath = path.resolve(projectRoot, pagePropsPath)

    // Find user config
    const configPath = findOpenApiTsConfig(projectRoot)
    const shouldGenerateSdk = configPath || generateSdk

    // Generate OpenAPI types
    if (fs.existsSync(absoluteOpenapiPath) && shouldGenerateSdk) {
      const plugins = buildHeyApiPlugins(config)

      logger?.info("Generating TypeScript types...")
      if (configPath) {
        const relConfigPath = path.relative(projectRoot, configPath)
        logger?.info(`openapi-ts config: ${relConfigPath}`)
      }

      try {
        const outputPath = await runHeyApiGeneration(config, configPath, plugins, logger)
        result.generatedFiles.push(outputPath)
        result.generated = true
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        if (message.includes("not found") || message.includes("ENOENT") || message.includes("not installed")) {
          const zodHint = config.generateZod ? " zod" : ""
          const warning = `@hey-api/openapi-ts not installed - run: ${resolveInstallHint()} -D @hey-api/openapi-ts${zodHint}`
          result.warnings.push(warning)
          logger?.warn(warning)
        } else {
          result.errors.push(message)
          logger?.error(`Type generation failed: ${message}`)
        }
      }
    }

    // Generate page props types
    if (generatePageProps && fs.existsSync(absolutePagePropsPath)) {
      try {
        const changed = await emitPagePropsTypes(absolutePagePropsPath, output)
        const pagePropsOutput = path.join(output, "page-props.ts")
        if (changed) {
          result.generatedFiles.push(pagePropsOutput)
          result.generated = true
        } else {
          result.skippedFiles.push(pagePropsOutput)
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        result.errors.push(`Page props generation failed: ${message}`)
        logger?.error(`Page props generation failed: ${message}`)
      }
    }

    // Generate schema helper types
    const { generateSchemas, routesPath, schemasTsPath } = config
    if (generateSchemas && routesPath) {
      const absoluteRoutesPath = path.resolve(projectRoot, routesPath)
      if (fs.existsSync(absoluteRoutesPath)) {
        try {
          const changed = await emitSchemasTypes(absoluteRoutesPath, output, schemasTsPath)
          const schemasOutput = schemasTsPath ?? path.join(output, "schemas.ts")
          if (changed) {
            result.generatedFiles.push(schemasOutput)
            result.generated = true
          } else {
            result.skippedFiles.push(schemasOutput)
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error)
          result.errors.push(`Schema types generation failed: ${message}`)
          logger?.error(`Schema types generation failed: ${message}`)
        }
      }
    }
  } finally {
    result.durationMs = Date.now() - startTime
  }

  return result
}
