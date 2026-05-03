import { describe, expect, it } from "vitest"
import { parseBridgeSchema } from "../../src/shared/bridge-schema"

const baseBridgeConfig = {
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
  spa: null,
  executor: "node",
  logging: null,
  litestarVersion: "2.18.0",
} as const

describe("bridge schema appUrl", () => {
  it("accepts a string appUrl", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      appUrl: "http://127.0.0.1:8000",
    })

    expect(config.appUrl).toBe("http://127.0.0.1:8000")
  })

  it("accepts a null appUrl", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      appUrl: null,
    })

    expect(config.appUrl).toBeNull()
  })

  it("treats a missing appUrl as null for older bridge files", () => {
    const config = parseBridgeSchema(baseBridgeConfig)

    expect(config.appUrl).toBeNull()
  })
})

describe("bridge schema mode contract", () => {
  it("rejects alias modes because Python writes canonical modes", () => {
    for (const mode of ["htmx", "inertia", "ssr", "ssg"]) {
      expect(() => parseBridgeSchema({ ...baseBridgeConfig, mode })).toThrow(`"mode" must be one of`)
    }
  })
})
