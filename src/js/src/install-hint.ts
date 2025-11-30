export function resolveInstallHint(pkg = "@hey-api/openapi-ts"): string {
  const runtime = (process.env.LITESTAR_VITE_RUNTIME ?? "").toLowerCase()
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
 * Priority: explicit executor > LITESTAR_VITE_RUNTIME env > 'node' default
 *
 * @param pkg - The package command to execute (e.g., "@hey-api/openapi-ts -i schema.json -o src/types")
 * @param executor - Optional explicit executor override
 * @returns The full command string (e.g., "npx @hey-api/openapi-ts ..." or "bunx @hey-api/openapi-ts ...")
 */
export function resolvePackageExecutor(pkg: string, executor?: string): string {
  const runtime = (executor ?? process.env.LITESTAR_VITE_RUNTIME ?? "").toLowerCase()
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
