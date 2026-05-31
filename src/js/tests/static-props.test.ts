import fs from "node:fs"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import litestar from "../src"

describe("static props virtual module", () => {
  const originalEnv = { ...process.env }
  let tempDir: string

  const baseConfig = {
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
  }

  const createRuntimeConfig = (data: Record<string, unknown>): string => {
    tempDir = fs.mkdtempSync(path.join(process.cwd(), "vitest-static-props-"))
    const cfgPath = path.join(tempDir, ".litestar.json")
    fs.writeFileSync(cfgPath, JSON.stringify({ ...baseConfig, ...data }), "utf-8")
    process.env.LITESTAR_VITE_CONFIG_PATH = cfgPath
    return cfgPath
  }

  const cleanup = (): void => {
    if (tempDir) {
      try {
        fs.rmSync(tempDir, { recursive: true, force: true })
      } catch {
        // ignore
      }
    }
    delete process.env.LITESTAR_VITE_CONFIG_PATH
  }

  beforeEach(() => {
    vi.resetModules()
    process.env = { ...originalEnv }
    process.env.LITESTAR_VITE_CONFIG_PATH = path.join(process.cwd(), ".vitest-missing-litestar.json")
  })

  afterEach(() => {
    process.env = { ...originalEnv }
    cleanup()
    vi.restoreAllMocks()
  })

  it("includes static props plugin in plugin array", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })

    // Find the static props plugin
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")
    expect(staticPropsPlugin).toBeDefined()
  })

  it("resolves virtual:litestar-static-props module", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const resolved = staticPropsPlugin?.resolveId?.("virtual:litestar-static-props")
    expect(resolved).toBe("\0virtual:litestar-static-props")
  })

  it("does not resolve other module IDs", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const resolved = staticPropsPlugin?.resolveId?.("some-other-module")
    expect(resolved).toBeUndefined()
  })

  it("generates module with default export for static props", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App", version: "1.0.0" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    expect(moduleContent).toContain('export default {"appName":"Test App","version":"1.0.0"};')
  })

  it("generates named exports for valid identifiers", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App", $special: "value", _private: true },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    expect(moduleContent).toContain('export const appName = "Test App";')
    expect(moduleContent).toContain('export const $special = "value";')
    expect(moduleContent).toContain("export const _private = true;")
  })

  it("skips named exports for invalid identifiers", () => {
    createRuntimeConfig({
      staticProps: { "valid-key": "value", "123invalid": "value", "with spaces": "value" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    // These should NOT be named exports (invalid identifiers)
    expect(moduleContent).not.toContain("export const valid-key")
    expect(moduleContent).not.toContain("export const 123invalid")
    expect(moduleContent).not.toContain("export const with spaces")

    // But they should still be in the default export
    expect(moduleContent).toContain('"valid-key":"value"')
    expect(moduleContent).toContain('"123invalid":"value"')
    expect(moduleContent).toContain('"with spaces":"value"')
  })

  it("handles nested objects in static props", () => {
    createRuntimeConfig({
      staticProps: {
        app: { name: "My App", version: "2.0" },
        features: { darkMode: true, analytics: false },
      },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    // Named exports for valid top-level keys
    expect(moduleContent).toContain('export const app = {"name":"My App","version":"2.0"};')
    expect(moduleContent).toContain('export const features = {"darkMode":true,"analytics":false};')
  })

  it("handles empty static props", () => {
    createRuntimeConfig({
      staticProps: null,
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    expect(moduleContent).toContain("export default {};")
  })

  it("handles missing .litestar.json gracefully", () => {
    // Use the missing config path (set in beforeEach)
    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    // Should return empty props
    expect(moduleContent).toContain("export default {};")
  })

  it("does not load other module IDs", () => {
    createRuntimeConfig({
      staticProps: { appName: "Test App" },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("some-other-module")
    expect(moduleContent).toBeUndefined()
  })

  it("handles arrays in static props", () => {
    createRuntimeConfig({
      staticProps: {
        tags: ["web", "python", "typescript"],
        numbers: [1, 2, 3],
      },
    })

    const plugins = litestar({ input: "resources/js/app.ts", types: false })
    const staticPropsPlugin = plugins.find((p: any) => p.name === "litestar-vite-static-props")

    const moduleContent = staticPropsPlugin?.load?.("\0virtual:litestar-static-props")

    expect(moduleContent).toContain('export const tags = ["web","python","typescript"];')
    expect(moduleContent).toContain("export const numbers = [1,2,3];")
  })
})
