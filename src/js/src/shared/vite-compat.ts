import { version } from "vite"

const [viteMajorRaw, viteMinorRaw] = version.split(".")

/** Parsed major version of the running Vite instance. */
export const viteMajor = Number(viteMajorRaw)
/** Parsed minor version of the running Vite instance. */
export const viteMinor = Number(viteMinorRaw)

/**
 * Whether the running Vite version is 8+, which uses Rolldown and exposes
 * `build.rolldownOptions` in place of Vite 7's `build.rollupOptions`.
 */
export const isVite8Plus: boolean = viteMajor >= 8

/**
 * Whether the running Vite version is 8.1+, which moved the HMR network options
 * (`host`/`protocol`/`port`/`clientPort`/`path`/`timeout`) from `server.hmr.*`
 * to `server.ws.*`. On 8.1+ `server.hmr` only carries the enable/disable toggle.
 */
export const isVite81Plus: boolean = viteMajor > 8 || (viteMajor === 8 && viteMinor >= 1)

/**
 * Returns a `build` config fragment with the input placed under the bundler key
 * for the running Vite version (`rolldownOptions` on 8+, `rollupOptions` on 7).
 */
export function buildInputOptions(input: string | string[] | undefined): Record<string, unknown> {
  if (input === undefined) return {}
  const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
  return { [key]: { input } }
}

/**
 * Reads the user-provided build input, preferring the version-appropriate key
 * and falling back to the other so configs migrated across a Vite major still work.
 */
export function resolveUserBuildInput(userBuild: Record<string, any> | undefined): string | string[] | undefined {
  if (!userBuild) return undefined
  return isVite8Plus ? (userBuild.rolldownOptions?.input ?? userBuild.rollupOptions?.input) : (userBuild.rollupOptions?.input ?? userBuild.rolldownOptions?.input)
}

/**
 * Returns a `build` config fragment with arbitrary options placed under the
 * bundler key for the running Vite version.
 */
export function buildBundlerOptions(options: Record<string, unknown>): Record<string, unknown> {
  const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
  return { [key]: options }
}

/**
 * Wraps HMR network options under the correct server key for the running Vite
 * version: `server.ws` on 8.1+, `server.hmr` on 8.0 / 7. Lets the plugin and
 * integrations emit one shape that is deprecation-free on every supported Vite.
 */
export function hmrServerConfig(network: Record<string, unknown>): Record<string, unknown> {
  return isVite81Plus ? { ws: network } : { hmr: network }
}
