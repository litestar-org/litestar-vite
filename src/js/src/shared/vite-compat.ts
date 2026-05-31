import { version } from "vite"

/**
 * Parsed major version of the running Vite instance.
 */
export const viteMajor = Number(version.split(".")[0])

/**
 * Whether the running Vite version is 8+, which uses Rolldown
 * instead of Rollup and introduces `rolldownOptions` / `rolldownOptions`
 * in place of the deprecated `rollupOptions` / `esbuildOptions`.
 */
export const isVite8Plus: boolean = viteMajor >= 8

/**
 * Returns a `build` config fragment with the input placed under
 * the correct key for the running Vite version.
 *
 * Vite 8+ uses `rolldownOptions`; Vite 7 uses `rollupOptions`.
 * Both accept the same `input` shape.
 */
export function buildInputOptions(input: string | string[] | undefined): Record<string, unknown> {
  if (input === undefined) return {}
  const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
  return { [key]: { input } }
}

/**
 * Reads the user-provided `build.rollupOptions.input` or
 * `build.rolldownOptions.input`, preferring the version-appropriate key.
 */
export function resolveUserBuildInput(userBuild: Record<string, any> | undefined): string | string[] | undefined {
  if (!userBuild) return undefined
  if (isVite8Plus) {
    return userBuild.rolldownOptions?.input ?? userBuild.rollupOptions?.input
  }
  return userBuild.rollupOptions?.input ?? userBuild.rolldownOptions?.input
}

/**
 * Returns a `build` config fragment with arbitrary options placed under
 * the correct bundler key for the running Vite version.
 */
export function buildBundlerOptions(options: Record<string, unknown>): Record<string, unknown> {
  const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
  return { [key]: options }
}
