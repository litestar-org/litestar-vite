/**
 * Unified TypeScript type generation CLI.
 *
 * This is the single CLI entry point for type generation, used by:
 * - `litestar assets generate-types` (via subprocess)
 *
 * Reads configuration from .litestar.json in the current directory.
 *
 * Usage: litestar-vite-typegen [--verbose]
 */
import colors from "picocolors"

import { readBridgeConfig } from "./shared/bridge-schema.js"
import { runTypeGeneration, type TypeGenCoreConfig, type TypeGenLogger } from "./shared/typegen-core.js"

interface CliOptions {
  verbose: boolean
}

function parseArgs(): CliOptions {
  const args = process.argv.slice(2)
  return {
    verbose: args.includes("--verbose"),
  }
}

function log(message: string): void {
  console.log(message)
}

function logError(message: string): void {
  console.error(message)
}

/**
 * Create a logger that writes to console with colored output.
 */
function createConsoleLogger(): TypeGenLogger {
  return {
    info: (message: string) => log(`${colors.cyan("•")} ${message}`),
    warn: (message: string) => log(`${colors.yellow("!")} ${message}`),
    error: (message: string) => logError(`${colors.red("✗")} ${message}`),
  }
}

async function main(): Promise<void> {
  parseArgs() // Parse args for future use (currently no-op)
  const projectRoot = process.cwd()

  // Read .litestar.json config
  const bridgeConfig = readBridgeConfig()
  if (!bridgeConfig) {
    logError(`${colors.red("✗")} .litestar.json not found`)
    logError("  Run 'litestar run' or 'litestar assets generate-types' first to generate it.")
    process.exit(1)
  }

  const typesConfig = bridgeConfig.types
  if (!typesConfig || !typesConfig.enabled) {
    log(`${colors.yellow("!")} Type generation is disabled in configuration`)
    process.exit(0)
  }

  // Build core config from bridge config
  const coreConfig: TypeGenCoreConfig = {
    projectRoot,
    openapiPath: typesConfig.openapiPath,
    output: typesConfig.output,
    pagePropsPath: typesConfig.pagePropsPath,
    routesPath: typesConfig.routesPath,
    generateSdk: typesConfig.generateSdk,
    generateZod: typesConfig.generateZod,
    generatePageProps: typesConfig.generatePageProps,
    generateSchemas: typesConfig.generateSchemas ?? true, // Default to true
    schemasTsPath: typesConfig.schemasTsPath,
    sdkClientPlugin: "@hey-api/client-axios", // Default for CLI (matches Vite plugin + templates)
    executor: bridgeConfig.executor,
  }

  const logger = createConsoleLogger()

  // Run type generation (CLI always runs - no caching)
  const result = await runTypeGeneration(coreConfig, { logger })

  // Handle errors
  if (result.errors.length > 0) {
    process.exit(1)
  }

  // Report skipped files with user-friendly names
  for (const file of result.skippedFiles) {
    const name = file.includes("page-props") ? "Page props types" : file
    log(`${colors.cyan("•")} ${name} ${colors.dim("(unchanged)")}`)
  }

  // Summary
  if (result.generated) {
    log(`${colors.green("✓")} TypeScript artifacts updated ${colors.dim(`(${result.durationMs}ms)`)}`)
  }
}

main().catch((error) => {
  logError(`${colors.red("✗")} Unexpected error: ${error instanceof Error ? error.message : String(error)}`)
  process.exit(1)
})
