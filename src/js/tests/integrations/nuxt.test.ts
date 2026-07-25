import fs from "node:fs"
import path from "node:path"
import { describe, expect, it, vi } from "vitest"
import litestarNuxtModule from "../../src/nuxt"
import { getHmrNetworkConfig } from "../__fixtures__/mock-vite-config"

describe("litestar-nuxt integration", () => {
  it("advertises Nuxt 4 compatibility", () => {
    expect(litestarNuxtModule.meta).toMatchObject({
      configKey: "litestar",
      compatibility: {
        nuxt: ">=4.0.0",
      },
    })
  })

  it("writes the primary hotfile only after Nuxt starts listening", () => {
    const hotFile = path.resolve(process.cwd(), "public", "hot")
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
    const mkdir = vi.spyOn(fs, "mkdirSync").mockImplementation(() => undefined)
    const writeFile = vi.spyOn(fs, "writeFileSync").mockImplementation(() => undefined)
    let listenHook: ((_server: unknown, listener: unknown) => void) | undefined
    const hook = vi.fn((name: string, callback: (_server: unknown, listener: unknown) => void) => {
      if (name === "listen") {
        listenHook = callback
      }
    })
    process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/.litestar.json"
    const nuxt = { options: { vite: {}, runtimeConfig: {}, nitro: {} }, hook }

    try {
      litestarNuxtModule({}, nuxt as any)

      expect(writeFile).not.toHaveBeenCalled()
      expect(hook).toHaveBeenCalledWith("listen", expect.any(Function))

      listenHook?.(undefined, {
        url: "http://localhost:4789/",
        address: { address: "0.0.0.0", family: "IPv4", port: 4789 },
      })

      expect(mkdir).toHaveBeenCalledWith(path.dirname(hotFile), { recursive: true })
      expect(writeFile).toHaveBeenCalledOnce()
      expect(writeFile).toHaveBeenCalledWith(hotFile, "http://localhost:4789")
    } finally {
      vi.restoreAllMocks()
      delete process.env.LITESTAR_VITE_CONFIG_PATH
    }
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
      const hmr = getHmrNetworkConfig(cfg)
      expect(hmr?.clientPort).toBe(8000)
      expect(hmr?.path).toBe("/static/vite-hmr")
      expect(hmr?.protocol).toBe("ws")
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
