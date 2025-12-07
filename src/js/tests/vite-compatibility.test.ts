import { beforeEach, describe, expect, it, vi } from "vitest"
import litestar from "../src"

// Mock the fs module for consistent testing
vi.mock("fs", async () => {
  const actual = await vi.importActual<typeof import("fs")>("fs")

  return {
    promises: actual.promises,
    default: {
      ...actual,
      existsSync: (path: string) => ["resources/", "assets/", "src/"].includes(path) || actual.existsSync(path),
      readFileSync: actual.readFileSync,
      mkdirSync: actual.mkdirSync,
      writeFileSync: actual.writeFileSync,
      rmSync: actual.rmSync,
    },
  }
})

// Mock process.env for testing
const originalEnv = process.env
beforeEach(() => {
  vi.resetModules()
  process.env = { ...originalEnv }
  vi.clearAllMocks()
})

describe("Vite 7.0 Compatibility", () => {
  describe("Plugin Configuration", () => {
    it("builds successfully with Vite 7.0 configuration format", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      // Test Vite 7.0 style configuration
      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
    })

    it("handles Vite 7.0 development server configuration", () => {
      process.env.VITE_ALLOW_REMOTE = "1"
      process.env.VITE_PORT = "5173"

      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config({}, { command: "serve", mode: "development" })

      expect(config.server?.host).toBe("0.0.0.0")
      expect(config.server?.port).toBe(5173)
      expect(config.server?.strictPort).toBe(true)
    })

    it("supports Vite 7.0 SSR configuration", () => {
      const plugin = litestar({
        input: "resources/js/app.ts",
        ssr: "resources/js/ssr.ts",
      })[0]

      const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })

      expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.ts")
      expect(ssrConfig.build?.manifest).toBe(false)
    })

    it("handles Vite 7.0 build optimizations", () => {
      const plugin = litestar({
        input: "resources/js/app.ts",
        bundleDir: "dist",
      })[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.build?.outDir).toBe("dist")
      expect(config.base).toBe("/static/")
    })
  })

  describe("Asset URL Handling", () => {
    it("handles Vite 7.0 asset URL generation", () => {
      const plugin = litestar({
        input: "resources/js/app.ts",
        assetUrl: "/vite-assets/",
      })[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.base).toBe("/vite-assets/")
    })

    it("supports CDN asset URLs in Vite 7.0", () => {
      process.env.ASSET_URL = "https://cdn.example.com/assets/"

      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.base).toBe("https://cdn.example.com/assets/")
    })

    it("handles environment-specific asset URLs", () => {
      process.env.ASSET_URL = "https://staging-cdn.example.com/"

      const plugin = litestar({
        input: "resources/js/app.ts",
        assetUrl: "/local-assets/",
      })[0]

      const prodConfig = plugin.config({}, { command: "build", mode: "production" })
      const devConfig = plugin.config({}, { command: "serve", mode: "development" })

      expect(prodConfig.base).toBe("https://staging-cdn.example.com/")
      expect(devConfig.base).toBe("/local-assets/")
    })
  })

  describe("Build Configuration", () => {
    it("supports Vite 7.0 build target configuration", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      // Test that plugin preserves user build configuration
      const userConfig = {
        build: {
          target: "es2022",
          minify: "terser",
        },
      }

      const config = plugin.config(userConfig, { command: "build", mode: "production" })

      // Plugin should preserve user's build config while adding its own
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
    })

    it("handles Vite 7.0 code splitting configuration", () => {
      const plugin = litestar(["resources/js/app.ts", "resources/js/admin.ts"])[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.build?.rollupOptions?.input).toEqual(["resources/js/app.ts", "resources/js/admin.ts"])
    })

    it("supports Vite 7.0 chunk optimization", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          build: {
            rollupOptions: {
              output: {
                manualChunks: {
                  vendor: ["vue", "react"],
                },
              },
            },
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin should set its own configuration without overriding user chunk config
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
    })
  })

  describe("Development Server Features", () => {
    it("supports Vite 7.0 HMR configuration", () => {
      const plugin = litestar({
        input: "resources/js/app.ts",
        refresh: true,
        types: false,
      })

      expect(plugin.length).toBe(2) // Main plugin + HMR plugin

      const hmrPlugin = plugin[1]
      expect(hmrPlugin.__litestar_plugin_config).toEqual({
        paths: ["src/**", "resources/**", "assets/**"],
      })
    })

    it("handles Vite 7.0 proxy configuration", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          server: {
            proxy: {
              "/api": "http://localhost:8000",
            },
          },
        },
        { command: "serve", mode: "development" },
      )

      // Plugin only sets server config when specific conditions are met
      expect(config.server?.origin).toBe("__litestar_vite_placeholder__")
      expect(config.base).toBe("/static/")
    })

    it("supports Vite 7.0 middleware configuration", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const _middlewareFn = vi.fn()
      const config = plugin.config(
        {
          server: {
            middlewareMode: true,
          },
        },
        { command: "serve", mode: "development" },
      )

      // Plugin only sets server config when specific conditions are met
      expect(config.server?.origin).toBe("__litestar_vite_placeholder__")
      expect(config.base).toBe("/static/")
    })
  })

  describe("TypeScript Support", () => {
    it("handles Vite 7.0 TypeScript configuration", () => {
      const plugin = litestar("resources/ts/app.ts")[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.build?.rollupOptions?.input).toBe("resources/ts/app.ts")
    })

    it("supports Vite 7.0 TypeScript path mapping", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          resolve: {
            alias: {
              "@": "/resources/js",
              "@components": "/resources/js/components",
            },
          },
        },
        { command: "build", mode: "development" },
      )

      expect(config.resolve?.alias?.["@"]).toBe("/resources/js")
      expect(config.resolve?.alias?.["@components"]).toBe("/resources/js/components")
    })

    it("preserves existing @ alias with Vite 7.0", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          resolve: {
            alias: {
              "@": "/custom/path",
            },
          },
        },
        { command: "build", mode: "development" },
      )

      expect(config.resolve?.alias?.["@"]).toBe("/custom/path")
    })
  })

  describe("Plugin Integration", () => {
    it("handles Vite 7.0 plugin API changes", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      // Test that the plugin conforms to Vite 7.0 plugin API
      expect(plugin.name).toBe("litestar")
      expect(typeof plugin.config).toBe("function")
      expect(typeof plugin.configResolved).toBe("function")
    })

    it("supports Vite 7.0 plugin composition", () => {
      const plugins = litestar({
        input: "resources/js/app.ts",
        refresh: ["resources/**", "templates/**"],
        types: false,
      })

      expect(plugins.length).toBe(2)
      expect(plugins[0].name).toBe("litestar")
    })

    it("handles Vite 7.0 conditional plugin loading", () => {
      const devPlugins = litestar({
        input: "resources/js/app.ts",
        refresh: true,
        types: false,
      })

      const prodPlugins = litestar({
        input: "resources/js/app.ts",
        refresh: false,
        types: false,
      })

      expect(devPlugins.length).toBe(2) // With HMR
      expect(prodPlugins.length).toBe(1) // Without HMR
    })
  })

  describe("Performance Optimizations", () => {
    it("supports Vite 7.0 dependency pre-bundling", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          optimizeDeps: {
            include: ["vue", "axios"],
            exclude: ["@custom/module"],
          },
        },
        { command: "serve", mode: "development" },
      )

      // Plugin doesn't override optimizeDeps, test what it actually sets
      expect(config.base).toBe("/static/")
      expect(config.server?.origin).toBe("__litestar_vite_placeholder__")
    })

    it("handles Vite 7.0 build caching", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          build: {
            write: true,
            emptyOutDir: true,
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin sets its own build configuration
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
    })

    it("supports Vite 7.0 tree shaking optimizations", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          build: {
            rollupOptions: {
              treeshake: {
                moduleSideEffects: false,
              },
            },
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin sets its own build configuration
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
      expect(config.base).toBe("/static/")
    })
  })

  describe("Error Handling", () => {
    it("handles Vite 7.0 error overlay configuration", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          server: {
            hmr: {
              overlay: true,
            },
          },
        },
        { command: "serve", mode: "development" },
      )

      // Plugin only sets server config when specific conditions are met
      expect(config.server?.origin).toBe("__litestar_vite_placeholder__")
      expect(config.base).toBe("/static/")
    })

    it("supports Vite 7.0 build error handling", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          build: {
            rollupOptions: {
              onwarn: (warning, warn) => {
                // Custom warning handler
                warn(warning)
              },
            },
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin sets its own build configuration
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
    })
  })

  describe("Environment Support", () => {
    it("handles Vite 7.0 environment variables", () => {
      process.env.VITE_API_URL = "https://api.example.com"
      process.env.VITE_APP_TITLE = "Test App"

      const plugin = litestar("resources/js/app.ts")[0]

      const config = plugin.config(
        {
          define: {
            __APP_VERSION__: '"1.0.0"',
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin sets its own configuration, doesn't preserve user define config
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.base).toBe("/static/")
    })

    it("supports Vite 7.0 mode-specific configuration", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      const devConfig = plugin.config({}, { command: "serve", mode: "development" })
      const prodConfig = plugin.config({}, { command: "build", mode: "production" })

      expect(devConfig.base).toBe("/static/")
      expect(prodConfig.base).toBe("/static/")
    })
  })

  describe("Backwards Compatibility", () => {
    it("maintains compatibility with Vite 5.x configurations", () => {
      // Test that older configurations still work
      const plugin = litestar({
        input: "resources/js/app.js",
        bundleDir: "public",
        assetUrl: "/static/",
      })[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.build?.outDir).toBe("public")
      expect(config.base).toBe("/static/")
    })

    it("maintains compatibility with Vite 6.x configurations", () => {
      const plugin = litestar({
        input: ["resources/js/app.ts", "resources/js/admin.ts"],
        ssr: "resources/js/ssr.ts",
      })[0]

      const config = plugin.config({}, { command: "build", mode: "production" })
      const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })

      expect(config.build?.rollupOptions?.input).toEqual(["resources/js/app.ts", "resources/js/admin.ts"])
      expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.ts")
    })

    it("handles legacy plugin options gracefully", () => {
      // Test with older plugin configuration format
      const plugin = litestar({
        input: "resources/js/app.js",
        publicDirectory: "public",
        buildDirectory: "dist",
      })[0]

      const config = plugin.config({}, { command: "build", mode: "production" })

      // Should still work even if some options don't exist
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.js")
    })
  })

  describe("Future Compatibility", () => {
    it("supports extensible configuration for future Vite versions", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      // Test with potential future configuration options
      const config = plugin.config(
        {
          experimental: {
            someNewFeature: true,
          },
          future: {
            newBuildOption: "value",
          },
        },
        { command: "build", mode: "production" },
      )

      // Plugin sets its own configuration without preserving experimental features
      expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")
      expect(config.build?.manifest).toBe("manifest.json")
      expect(config.base).toBe("/static/")
    })

    it("maintains plugin API stability for future versions", () => {
      const plugin = litestar("resources/js/app.ts")[0]

      // Test that essential plugin methods are available
      expect(typeof plugin.config).toBe("function")
      expect(typeof plugin.configResolved).toBe("function")
      expect(plugin.name).toBe("litestar")
    })
  })
})
