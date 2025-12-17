import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { loadLitestarMeta } from "../src/litestar-meta"

describe("litestar-meta runtime config fallback", () => {
  const originalEnv = { ...process.env }

  afterEach(() => {
    process.env = { ...originalEnv }
  })

  const makeTempRuntimeConfig = (version: string): string => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "litevite-"))
    const cfgPath = path.join(dir, ".litestar.json")
    const payload = {
      assetUrl: "/static",
      deployAssetUrl: null,
      bundleDir: "public",
      resourceDir: "resources",
      staticDir: "public",
      hotFile: "hot",
      manifest: "manifest.json",
      mode: "spa",
      proxyMode: "vite",
      host: "localhost",
      port: 5173,
      ssrOutDir: null,
      types: null,
      executor: "node",
      logging: null,
      litestarVersion: version,
    }
    fs.writeFileSync(cfgPath, JSON.stringify(payload), "utf8")
    return cfgPath
  }

  it("reads litestarVersion from runtime config when env and routes are absent", async () => {
    const cfgPath = makeTempRuntimeConfig("9.9.9")
    delete process.env.LITESTAR_VERSION
    process.env.LITESTAR_VITE_CONFIG_PATH = cfgPath

    const meta = await loadLitestarMeta({ root: process.cwd() } as any)

    expect(meta.litestarVersion).toBe("9.9.9")
  })
})
