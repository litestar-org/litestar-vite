import fs from "node:fs"
import path from "node:path"

/**
 * Detect the executor from .litestar.json or environment.
 * Priority: LITESTAR_VITE_RUNTIME env > .litestar.json executor > lockfile detection > 'node'
 */
export function detectExecutor(): string {
  // 1. Check environment variable
  const envRuntime = (process.env.LITESTAR_VITE_RUNTIME ?? "").toLowerCase()
  if (envRuntime) return envRuntime

  // 2. Check .litestar.json
  const configPath = process.env.LITESTAR_VITE_CONFIG_PATH ?? path.resolve(process.cwd(), ".litestar.json")
  if (fs.existsSync(configPath)) {
    try {
      const raw = fs.readFileSync(configPath, "utf8")
      const data = JSON.parse(raw) as Record<string, unknown>
      const executor = data?.executor
      if (typeof executor === "string" && executor.trim()) {
        return executor.trim().toLowerCase()
      }
    } catch {
      // Ignore parse errors
    }
  }

  // 3. Detect from lockfiles
  const cwd = process.cwd()
  if (fs.existsSync(path.join(cwd, "bun.lockb")) || fs.existsSync(path.join(cwd, "bun.lock"))) {
    return "bun"
  }
  if (fs.existsSync(path.join(cwd, "pnpm-lock.yaml"))) {
    return "pnpm"
  }
  if (fs.existsSync(path.join(cwd, "yarn.lock"))) {
    return "yarn"
  }
  if (fs.existsSync(path.join(cwd, "deno.lock"))) {
    return "deno"
  }

  return "node"
}

export function resolveInstallHint(pkg = "@hey-api/openapi-ts"): string {
  const runtime = detectExecutor()
  switch (runtime) {
    case "bun":
      return `bun add -d ${pkg}`
    case "deno":
      return `deno add -d npm:${pkg}`
    case "pnpm":
      return `pnpm add -D ${pkg}`
    case "yarn":
      return `yarn add -D ${pkg}`
  }

  const envInstall = process.env.LITESTAR_VITE_INSTALL_CMD?.trim()
  if (envInstall) {
    return `${envInstall} -D ${pkg}`
  }

  return `npm install -D ${pkg}`
}

/**
 * Resolves the package executor command based on runtime.
 * Priority: explicit executor > .litestar.json > LITESTAR_VITE_RUNTIME env > lockfile detection > 'npx'
 *
 * @param pkg - The package command to execute (e.g., "@hey-api/openapi-ts -i schema.json -o src/types")
 * @param executor - Optional explicit executor override
 * @returns The full command string (e.g., "npx @hey-api/openapi-ts ..." or "bunx @hey-api/openapi-ts ...")
 */
export function resolvePackageExecutor(pkg: string, executor?: string): string {
  // Use || to treat empty string as falsy, triggering detection
  const runtime = executor || detectExecutor()
  switch (runtime) {
    case "bun":
      return `bunx ${pkg}`
    case "deno":
      return `deno run -A npm:${pkg}`
    case "pnpm":
      return `pnpm dlx ${pkg}`
    case "yarn":
      return `yarn dlx ${pkg}`
    default:
      return `npx ${pkg}`
  }
}
