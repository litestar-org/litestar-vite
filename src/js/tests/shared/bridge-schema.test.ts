import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { describe, expect, it, vi } from "vitest"
import { parseBridgeSchema, readBridgeConfig } from "../../src/shared/bridge-schema"

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

describe("bridge schema litestarPort", () => {
  it("accepts a numeric litestarPort", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, litestarPort: 8000 })
    expect(config.litestarPort).toBe(8000)
  })

  it("accepts a null litestarPort", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, litestarPort: null })
    expect(config.litestarPort).toBeNull()
  })

  it("treats a missing litestarPort as null for older bridge files", () => {
    const config = parseBridgeSchema(baseBridgeConfig)
    expect(config.litestarPort).toBeNull()
  })

  it("rejects non-integer litestarPort", () => {
    expect(() => parseBridgeSchema({ ...baseBridgeConfig, litestarPort: "8000" })).toThrow(/litestarPort/)
  })
})

describe("bridge schema additive fields", () => {
  it("warns and ignores unknown top-level keys", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, futureField: true })

    expect(config.assetUrl).toBe("/static")
    expect("futureField" in config).toBe(false)
  })

  it("returns null for corrupt bridge JSON", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-bridge-"))
    const configPath = path.join(tmpDir, ".litestar.json")
    fs.writeFileSync(configPath, "{")

    try {
      expect(readBridgeConfig(configPath)).toBeNull()
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })

  it("memoizes bridge file reads until path mtime changes", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-bridge-"))
    const configPath = path.join(tmpDir, ".litestar.json")
    fs.writeFileSync(configPath, JSON.stringify(baseBridgeConfig))
    const readSpy = vi.spyOn(fs, "readFileSync")

    try {
      expect(readBridgeConfig(configPath)?.port).toBe(5173)
      expect(readBridgeConfig(configPath)?.port).toBe(5173)
      expect(readSpy).toHaveBeenCalledTimes(1)

      fs.writeFileSync(configPath, JSON.stringify({ ...baseBridgeConfig, port: 5174 }))
      const mtime = new Date(Date.now() + 1000)
      fs.utimesSync(configPath, mtime, mtime)

      expect(readBridgeConfig(configPath)?.port).toBe(5174)
      expect(readSpy).toHaveBeenCalledTimes(2)
    } finally {
      readSpy.mockRestore()
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })
})

describe("bridge schema typegen failOnError", () => {
  const types = {
    enabled: true,
    output: "src/generated",
    openapiPath: "src/generated/openapi.json",
    routesPath: "src/generated/routes.json",
    pagePropsPath: "src/generated/inertia-pages.json",
    generateZod: false,
    generateSdk: true,
    generateRoutes: true,
    generatePageProps: true,
    generateSchemas: true,
    globalRoute: false,
  }

  it("parses an explicit failOnError value", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, types: { ...types, failOnError: false } })

    expect(config.types?.failOnError).toBe(false)
  })

  it("preserves failOnError as undefined when the bridge omits it or writes null", () => {
    const omitted = parseBridgeSchema({ ...baseBridgeConfig, types })
    const nullValue = parseBridgeSchema({ ...baseBridgeConfig, types: { ...types, failOnError: null } })

    expect(omitted.types?.failOnError).toBeUndefined()
    expect(nullValue.types?.failOnError).toBeUndefined()
  })
})
