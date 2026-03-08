import { describe, expect, it } from "vitest"
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
