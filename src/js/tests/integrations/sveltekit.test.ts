import fs from "node:fs"

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { litestarSvelteKit } from "../../src/sveltekit"

const baseRuntimeConfig = {
  assetUrl: "/static",
  deployAssetUrl: null,
  appUrl: null,
  litestarPort: null,
  bundleDir: "public",
  resourceDir: "resources",
  staticDir: "public",
  hotFile: "hot",
  manifest: "manifest.json",
  mode: "framework",
  proxyMode: "vite",
  host: "localhost",
  port: 5173,
  ssrOutDir: null,
  types: null,
  executor: "node",
  logging: null,
  litestarVersion: "2.18.0",
} as const

function runtimeConfig(overrides: Record<string, unknown> = {}): string {
  return JSON.stringify({ ...baseRuntimeConfig, ...overrides })
}

describe("litestar-sveltekit integration", () => {
  beforeEach(() => {
    vi.spyOn(fs, "existsSync").mockReturnValue(false)
    vi.spyOn(fs, "readFileSync").mockReturnValue("")
    delete process.env.LITESTAR_VITE_CONFIG_PATH
    delete process.env.LITESTAR_PORT
    delete process.env.PORT
    delete process.env.APP_URL
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete process.env.LITESTAR_VITE_CONFIG_PATH
    delete process.env.LITESTAR_PORT
    delete process.env.PORT
    delete process.env.APP_URL
  })

  it("returns a Vite plugin array", () => {
    const plugins = litestarSvelteKit({ apiProxy: "http://127.0.0.1:8000" })
    expect(Array.isArray(plugins)).toBe(true)
    expect(plugins[0]?.name).toBe("litestar-sveltekit")
  })

  it("sets vite.server.hmr.clientPort to the Litestar port from bridge", () => {
    process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/.litestar.json"
    ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
    ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(runtimeConfig({ appUrl: "http://127.0.0.1:8000", litestarPort: 8000 }))

    const plugins = litestarSvelteKit({ apiProxy: "http://127.0.0.1:8000" })
    const main = plugins[0]
    const cfg = main.config()
    expect(cfg.server.hmr).toMatchObject({
      protocol: "ws",
      host: "127.0.0.1",
      clientPort: 8000,
      path: "/static/vite-hmr",
    })
  })

  it("falls back to parsing appUrl when bridge lacks litestarPort", () => {
    process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/.litestar.json"
    ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
    ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(runtimeConfig({ appUrl: "http://127.0.0.1:9100" }))

    const plugins = litestarSvelteKit()
    const main = plugins[0]
    const cfg = main.config()
    expect(cfg.server.hmr.clientPort).toBe(9100)
  })

  it("omits hmr config when no Litestar port can be resolved", () => {
    const plugins = litestarSvelteKit()
    const main = plugins[0]
    const cfg = main.config()
    expect(cfg.server.hmr).toBeUndefined()
  })
})
