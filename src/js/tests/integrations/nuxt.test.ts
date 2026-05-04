import fs from "node:fs"

import { describe, expect, it, vi } from "vitest"

import litestarNuxtModule from "../../src/nuxt"

describe("litestar-nuxt integration", () => {
  it("advertises Nuxt 4 compatibility", () => {
    expect(litestarNuxtModule.meta).toMatchObject({
      configKey: "litestar",
      compatibility: {
        nuxt: ">=4.0.0",
      },
    })
  })

  it("sets vite.server.hmr.clientPort to the Litestar port from bridge", async () => {
    vi.spyOn(fs, "existsSync").mockReturnValue(true)
    vi.spyOn(fs, "readFileSync").mockReturnValue(
      JSON.stringify({
        assetUrl: "/static",
        deployAssetUrl: null,
        appUrl: "http://127.0.0.1:8000",
        litestarPort: 8000,
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
      }),
    )
    process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/.litestar.json"

    try {
      const nuxt = { options: { vite: {}, runtimeConfig: {}, nitro: {} } }
      litestarNuxtModule({ apiProxy: "http://127.0.0.1:8000" }, nuxt as any)

      const vitePlugins = (nuxt.options.vite as any).plugins as any[]
      const proxyPlugin = vitePlugins.find((p) => p.name === "litestar-nuxt-proxy")
      const cfg = await proxyPlugin.config()
      expect(cfg.server.hmr.clientPort).toBe(8000)
      expect(cfg.server.hmr.path).toBe("/static/vite-hmr")
      expect(cfg.server.hmr.protocol).toBe("ws")
    } finally {
      vi.restoreAllMocks()
      delete process.env.LITESTAR_VITE_CONFIG_PATH
    }
  })

  it("merges module options into vite, runtime config, and nitro devProxy", () => {
    const nuxt = {
      options: {
        vite: {},
        runtimeConfig: {},
        nitro: {},
      },
    }

    litestarNuxtModule(
      {
        apiProxy: "http://127.0.0.1:8000",
        apiPrefix: "/api",
        verbose: false,
      },
      nuxt,
    )

    expect(nuxt.options.vite.plugins).toBeDefined()
    expect(Array.isArray(nuxt.options.vite.plugins)).toBe(true)
    expect(nuxt.options.vite.plugins?.some((plugin: { name?: string }) => plugin.name === "litestar-nuxt-proxy")).toBe(true)

    expect(nuxt.options.runtimeConfig).toMatchObject({
      public: {
        apiProxy: "http://127.0.0.1:8000",
        apiPrefix: "/api",
      },
    })

    expect(nuxt.options.nitro).toMatchObject({
      devProxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          ws: true,
        },
      },
    })
  })
})
