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
