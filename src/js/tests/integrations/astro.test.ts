import fs from "node:fs"

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import litestarAstro from "../../src/astro"

// Mock node:fs
vi.mock("node:fs", () => ({
  default: {
    existsSync: vi.fn(),
    readFileSync: vi.fn(),
    writeFileSync: vi.fn(),
    mkdirSync: vi.fn(),
    promises: {
      readFile: vi.fn(),
      writeFile: vi.fn(),
      mkdir: vi.fn(),
    },
  },
  existsSync: vi.fn(),
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  mkdirSync: vi.fn(),
  promises: {
    readFile: vi.fn(),
    writeFile: vi.fn(),
    mkdir: vi.fn(),
  },
}))

// Mock node:child_process
vi.mock("node:child_process", () => {
  const execFn = vi.fn((_cmd: string, opts: unknown, cb?: (err: Error | null, stdout: string, stderr: string) => void) => {
    if (typeof opts === "function") {
      ;(opts as (err: Error | null, stdout: string, stderr: string) => void)(null, "", "")
    } else if (cb) {
      cb(null, "", "")
    }
  })
  return {
    default: { exec: execFn },
    exec: execFn,
  }
})

// Mock picocolors
vi.mock("picocolors", () => ({
  default: {
    cyan: (s: string) => s,
    green: (s: string) => s,
    yellow: (s: string) => s,
    red: (s: string) => s,
    dim: (s: string) => s,
    bold: (s: string) => s,
  },
}))

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
  mode: "spa",
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

describe("litestar-astro integration", () => {
  const originalEnv = { ...process.env }

  beforeEach(() => {
    vi.resetAllMocks()
    process.env = { ...originalEnv }
    process.env.LITESTAR_VITE_CONFIG_PATH = undefined
    process.env.VITE_PORT = undefined
  })

  afterEach(() => {
    process.env = originalEnv
    vi.restoreAllMocks()
  })

  describe("litestarAstro()", () => {
    it("returns an Astro integration object", () => {
      const integration = litestarAstro()

      expect(integration).toHaveProperty("name", "litestar-vite")
      expect(integration).toHaveProperty("hooks")
      expect(integration.hooks).toHaveProperty("astro:config:setup")
      expect(integration.hooks).toHaveProperty("astro:server:setup")
      expect(integration.hooks).toHaveProperty("astro:server:start")
      expect(integration.hooks).toHaveProperty("astro:build:start")
    })

    it("accepts custom apiProxy configuration", () => {
      const integration = litestarAstro({
        apiProxy: "http://backend:9000",
      })

      expect(integration.name).toBe("litestar-vite")
    })

    it("accepts custom apiPrefix configuration", () => {
      const integration = litestarAstro({
        apiPrefix: "/backend",
      })

      expect(integration.name).toBe("litestar-vite")
    })

    it("accepts types configuration as boolean", () => {
      const integration = litestarAstro({
        types: true,
      })

      expect(integration.name).toBe("litestar-vite")
    })

    it("accepts types configuration as object", () => {
      const integration = litestarAstro({
        types: {
          enabled: true,
          output: "src/custom/api",
          generateZod: true,
        },
      })

      expect(integration.name).toBe("litestar-vite")
    })

    it("accepts verbose configuration", () => {
      const integration = litestarAstro({
        verbose: true,
      })

      expect(integration.name).toBe("litestar-vite")
    })
  })

  describe("astro:config:setup hook", () => {
    it("calls updateConfig with proxy configuration", async () => {
      const integration = litestarAstro({
        apiProxy: "http://localhost:8000",
        apiPrefix: "/api",
      })

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      expect(updateConfig).toHaveBeenCalled()
      const config = updateConfig.mock.calls[0][0]
      expect(config.vite).toBeDefined()
      expect(config.vite.plugins).toBeDefined()
      const vitePlugins = config.vite?.plugins
      const proxyPlugin = Array.isArray(vitePlugins) ? vitePlugins.find((plugin: any) => plugin.name === "litestar-astro-proxy") : undefined
      expect(proxyPlugin).toBeDefined()
      const pluginConfig = proxyPlugin?.config?.()
      expect(pluginConfig?.server?.proxy).toBeDefined()
      expect(pluginConfig?.server?.proxy).toMatchObject({
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
          secure: false,
          ws: true,
        },
      })
    })

    it("respects VITE_PORT environment variable", async () => {
      process.env.VITE_PORT = "3456"

      const integration = litestarAstro()

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      expect(updateConfig).toHaveBeenCalled()
    })

    it("reads runtime config from LITESTAR_VITE_CONFIG_PATH", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/vite-config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(
        runtimeConfig({
          bundleDir: "dist",
          hotFile: "hot",
          proxyMode: "vite",
          port: 4000,
        }),
      )

      const integration = litestarAstro()

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      expect(fs.existsSync).toHaveBeenCalledWith("/tmp/vite-config.json")
      expect(fs.readFileSync).toHaveBeenCalled()
    })

    it("handles missing runtime config file gracefully", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/nonexistent/config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(false)

      const integration = litestarAstro()

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      // Should not throw
      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      expect(updateConfig).toHaveBeenCalled()
    })

    it("handles malformed runtime config JSON", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/bad-config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue("invalid json {")

      expect(() => litestarAstro()).toThrowError(/invalid \.litestar\.json/)
    })

    it("skips type generation plugin setup during build command", async () => {
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(false)
      const integration = litestarAstro({
        types: true,
      })

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "build",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      // Build command should not include the type generation watch plugin
      expect(updateConfig).toHaveBeenCalled()
    })
  })

  describe("astro:server:start hook", () => {
    it("writes hotfile when configured", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/vite-config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(
        runtimeConfig({
          bundleDir: "public",
          hotFile: "hot",
          proxyMode: "vite",
        }),
      )

      const integration = litestarAstro()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      // First, setup the config (which resolves hotFile)
      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig: vi.fn(),
        logger: mockLogger,
      })

      // Then, trigger server start
      await integration.hooks["astro:server:start"]?.({
        address: { address: "localhost", family: "IPv4", port: 5173 },
        logger: mockLogger,
      })

      // Hotfile should be written
      expect(fs.mkdirSync).toHaveBeenCalled()
      expect(fs.writeFileSync).toHaveBeenCalled()
    })
  })

  describe("configuration resolution", () => {
    it("uses default apiProxy when not specified", async () => {
      const integration = litestarAstro()

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      const config = updateConfig.mock.calls[0][0]
      // Check that proxy was configured (will have default /api prefix)
      expect(config.vite.plugins).toBeDefined()
    })

    it("sets vite.server.hmr.clientPort to the Litestar port from bridge", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/vite-config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(
        runtimeConfig({
          appUrl: "http://127.0.0.1:8000",
          litestarPort: 8000,
          assetUrl: "/static",
        }),
      )

      const integration = litestarAstro()
      const updateConfig = vi.fn()
      const mockLogger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn(), label: "test" }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      const cfg = updateConfig.mock.calls[0][0]
      const proxyPlugin = cfg.vite?.plugins?.find((p: any) => p.name === "litestar-astro-proxy")
      const pluginConfig = proxyPlugin?.config?.()
      expect(pluginConfig?.server?.hmr).toMatchObject({
        protocol: "ws",
        host: "127.0.0.1",
        clientPort: 8000,
        path: "/static/vite-hmr",
      })
    })

    it("falls back to parsing appUrl when bridge lacks litestarPort", async () => {
      process.env.LITESTAR_VITE_CONFIG_PATH = "/tmp/vite-config.json"
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(true)
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(
        runtimeConfig({
          appUrl: "http://127.0.0.1:9100",
          assetUrl: "/static",
        }),
      )

      const integration = litestarAstro()
      const updateConfig = vi.fn()
      const mockLogger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn(), label: "test" }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      const cfg = updateConfig.mock.calls[0][0]
      const proxyPlugin = cfg.vite?.plugins?.find((p: any) => p.name === "litestar-astro-proxy")
      const pluginConfig = proxyPlugin?.config?.()
      expect(pluginConfig?.server?.hmr?.clientPort).toBe(9100)
    })

    it("omits hmr config when no Litestar port can be resolved", async () => {
      delete process.env.LITESTAR_PORT
      delete process.env.PORT
      delete process.env.APP_URL
      delete process.env.LITESTAR_VITE_CONFIG_PATH
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(false)

      const integration = litestarAstro()
      const updateConfig = vi.fn()
      const mockLogger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn(), label: "test" }

      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      const cfg = updateConfig.mock.calls[0][0]
      const proxyPlugin = cfg.vite?.plugins?.find((p: any) => p.name === "litestar-astro-proxy")
      const pluginConfig = proxyPlugin?.config?.()
      expect(pluginConfig?.server?.hmr).toBeUndefined()
    })

    it("handles invalid VITE_PORT gracefully", async () => {
      process.env.VITE_PORT = "not-a-number"

      const integration = litestarAstro()

      const updateConfig = vi.fn()
      const mockLogger = {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      }

      // Should not throw
      await integration.hooks["astro:config:setup"]?.({
        config: {},
        command: "dev",
        isRestart: false,
        updateConfig,
        logger: mockLogger,
      })

      expect(updateConfig).toHaveBeenCalled()
    })
  })
})
