import fs from "node:fs"
import path from "node:path"
import type { ResolvedConfig } from "vite"

export interface LitestarMeta {
  litestarVersion?: string
}

function readJson(file: string): Record<string, unknown> | null {
  try {
    const raw = fs.readFileSync(file, "utf8")
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return null
  }
}

function firstExisting(paths: string[]): string | null {
  for (const p of paths) {
    if (fs.existsSync(p)) return p
  }
  return null
}

export async function loadLitestarMeta(resolvedConfig: ResolvedConfig, routesPathHint?: string): Promise<LitestarMeta> {
  const fromEnv = process.env.LITESTAR_VERSION?.trim()
  if (fromEnv) {
    return { litestarVersion: fromEnv }
  }

  const root = resolvedConfig.root ?? process.cwd()
  const candidates = [routesPathHint ? path.resolve(root, routesPathHint) : null, path.resolve(root, "src/generated/routes.json"), path.resolve(root, "routes.json")].filter(
    Boolean,
  ) as string[]

  const match = firstExisting(candidates)
  if (!match) return {}

  const data = readJson(match)
  if (!data) return {}

  const fromData = (key: string): string | null => {
    const value = (data as Record<string, unknown>)[key]
    return typeof value === "string" ? value : null
  }

  const litestarVersion: string | null = fromData("litestar_version") ?? fromData("litestarVersion") ?? fromData("version")

  return litestarVersion ? { litestarVersion } : {}
}
