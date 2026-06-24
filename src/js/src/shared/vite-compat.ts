/**
 * Returns a `build` config fragment with the input placed under
 * `rolldownOptions`, the Rolldown bundler key used by Vite 8.
 */
export function buildInputOptions(input: string | string[] | undefined): Record<string, unknown> {
  if (input === undefined) return {}
  return { rolldownOptions: { input } }
}

/**
 * Reads the user-provided build input from `rolldownOptions.input`,
 * falling back to the legacy `rollupOptions.input` key for configs
 * carried over from Vite 7.
 */
export function resolveUserBuildInput(userBuild: Record<string, any> | undefined): string | string[] | undefined {
  if (!userBuild) return undefined
  return userBuild.rolldownOptions?.input ?? userBuild.rollupOptions?.input
}

/**
 * Returns a `build` config fragment with arbitrary options placed under
 * the `rolldownOptions` bundler key.
 */
export function buildBundlerOptions(options: Record<string, unknown>): Record<string, unknown> {
  return { rolldownOptions: options }
}
