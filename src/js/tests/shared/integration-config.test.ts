import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../../src/shared/bridge-schema.js", () => ({
  readBridgeConfig: vi.fn(),
}))

import { readBridgeConfig } from "../../src/shared/bridge-schema.js"
import { resolveIntegrationConfig } from "../../src/shared/integration-config.js"

const mockedReadBridgeConfig = vi.mocked(readBridgeConfig)

function bridge(overrides: Record<string, unknown> = {}) {
  return {
    bundleDir: "dist",
    hotFile: "hot",
    proxyMode: "vite",
    port: 5173,
    litestarPort: 8000,
    assetUrl: "/static/",
    appUrl: null,
    executor: "pnpm",
    ...overrides,
  } as unknown as ReturnType<typeof readBridgeConfig>
}

beforeEach(() => {
  mockedReadBridgeConfig.mockReset()
  delete process.env.VITE_PORT
})

afterEach(() => {
  delete process.env.VITE_PORT
})

describe("resolveIntegrationConfig", () => {
  it("applies defaults when no bridge file is present", () => {
    mockedReadBridgeConfig.mockReturnValue(undefined as never)

    const resolved = resolveIntegrationConfig({}, "src/generated")

    expect(resolved.apiProxy).toBe("http://localhost:8000")
    expect(resolved.apiPrefix).toBe("/api")
    expect(resolved.verbose).toBe(false)
    expect(resolved.hasPythonConfig).toBe(false)
    expect(resolved.executor).toBeUndefined()
  })

  it("merges bridge-file values when present", () => {
    mockedReadBridgeConfig.mockReturnValue(bridge())

    const resolved = resolveIntegrationConfig({}, "src/generated")

    expect(resolved.hasPythonConfig).toBe(true)
    expect(resolved.proxyMode).toBe("vite")
    expect(resolved.port).toBe(5173)
    expect(resolved.litestarPort).toBe(8000)
    expect(resolved.assetUrl).toBe("/static/")
  })

  it("prefers an explicit executor over the one reported by Python", () => {
    mockedReadBridgeConfig.mockReturnValue(bridge({ executor: "pnpm" }))

    const resolved = resolveIntegrationConfig({ executor: "bun" }, "src/generated")

    expect(resolved.executor).toBe("bun")
  })

  it("falls back to the Python executor when none is configured", () => {
    mockedReadBridgeConfig.mockReturnValue(bridge({ executor: "pnpm" }))

    const resolved = resolveIntegrationConfig({}, "src/generated")

    expect(resolved.executor).toBe("pnpm")
  })

  it("reads the dev port from VITE_PORT when there is no bridge file", () => {
    mockedReadBridgeConfig.mockReturnValue(undefined as never)
    process.env.VITE_PORT = "4321"

    expect(resolveIntegrationConfig({}, "src/generated").port).toBe(4321)
  })

  it("ignores a non-numeric VITE_PORT", () => {
    mockedReadBridgeConfig.mockReturnValue(undefined as never)
    process.env.VITE_PORT = "not-a-port"

    expect(resolveIntegrationConfig({}, "src/generated").port).toBeUndefined()
  })

  it("threads the framework default output into type generation", () => {
    mockedReadBridgeConfig.mockReturnValue(undefined as never)

    const resolved = resolveIntegrationConfig({ types: true }, "src/lib/generated")

    expect(resolved.types).not.toBe(false)
    expect(resolved.types && resolved.types.output).toBe("src/lib/generated")
  })
})
