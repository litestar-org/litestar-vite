import fs from "node:fs"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import litestar from "../src"
import { resolvePageComponent } from "../src/inertia-helpers"

// Mock the fs module
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

// Read actual placeholder content for assertions (built file from dev-server/)
const actualPlaceholderContent = fs.readFileSync(path.resolve(__dirname, "../../../dist/js/dev-server-index.html"), "utf-8")

// Mock process.env
const originalEnv = process.env
beforeEach(() => {
  vi.resetModules()
  process.env = { ...originalEnv }
  // Ensure tests don't accidentally pick up a real repository `.litestar.json`.
  // If the env var is set but the file doesn't exist, the plugin treats bridge config as absent.
  process.env.LITESTAR_VITE_CONFIG_PATH = path.join(process.cwd(), ".vitest-missing-litestar.json")
  vi.clearAllMocks()
  vi.spyOn(fs.promises, "access").mockRestore()
  vi.spyOn(fs.promises, "readFile").mockRestore()
})

afterEach(() => {
  process.env = originalEnv
  vi.clearAllMocks()
  vi.restoreAllMocks()
})

// Mock routes for testing
beforeEach(() => {
  globalThis.routes = {
    home: "/",
    about: "/about",
    "users:assign-role": "/api/roles/{role_slug:str}/assign",
    "users:revoke-role": "/api/roles/{role_slug:str}/revoke",
    "tags:create": "/api/tags",
    "tags:list": "/api/tags",
    "tags:get": "/api/tags/{tag_id:uuid}",
    "tags:update": "/api/tags/{tag_id:uuid}",
    "tags:delete": "/api/tags/{tag_id:uuid}",
    "teams:add-member": "/api/teams/{team_id:uuid}/members/add",
    "teams:remove-member": "/api/teams/{team_id:uuid}/members/remove",
    "users:create": "/api/users/create",
    "users:list": "/api/users/list",
    "users:update": "/api/users/update/{user_id:uuid}",
    "users:delete": "/api/users/delete/{user_id:uuid}",
    "users:get": "/api/users/get/{user_id:uuid}",
    dashboard: "/dashboard",
    favicon: "/favicon.ico",
    landing: "/landing",
    "login.check": "/login/check",
    login: "/login",
    logout: "/logout",
    "github.complete": "/o/github/complete",
    "google.complete": "/o/google/complete",
    "privacy-policy": "/privacy-policy",
    "account.remove": "/profile/remove",
    "profile.show": "/profile",
    "profile.update": "/profile/update",
    "password.update": "/profile/password-update",
    register: "/register",
    "register.add": "/register/add",
    "github.register": "/register/github",
    "google.register": "/register/google",
    "worker:index": "/saq/queues/{queue_id:str}/jobs/{job_id:str}",
    "worker:queue-list": "/saq/api/queues/list",
    "worker:queue-detail": "/saq/api/queues/{queue_id:str}",
    "worker:job-detail": "/saq/api/queues/{queue_id:str}/jobs/{job_id:str}",
    "worker:job-abort": "/saq/api/queues/{queue_id:str}/jobs/{job_id:str}/abort",
    "worker:job-retry": "/saq/api/queues/{queue_id:str}/jobs/{job_id:str}/retry",
    saq: "/saq/static/{file_path:path}",
    vite: "/static/{file_path:path}",
    "teams.add": "/teams/add",
    "teams.list": "/teams/list",
    "teams.show": "/teams/show/{team_id:uuid}",
    "teams.remove": "/teams/remove/{team_id:uuid}",
    "teams.edit": "/teams/edit/{team_id:uuid}",
    "terms-of-service": "/terms-of-service",
  }
})

describe("litestar-vite-plugin", () => {
  const originalEnv = { ...process.env }

  afterEach(() => {
    process.env = { ...originalEnv }
    vi.resetAllMocks()
  })

  const baseTypesConfig = {
    enabled: true,
    output: "types/api",
    openapiPath: "openapi.json",
    routesPath: "routes.json",
    pagePropsPath: "page-props.json",
    generateZod: false,
    generateSdk: true,
    generateRoutes: true,
    generatePageProps: true,
    globalRoute: false,
  } as const

  const baseLoggingConfig = {
    level: "normal",
    showPathsAbsolute: false,
    suppressNpmOutput: true,
    suppressViteBanner: false,
    timestamps: false,
  } as const

  const baseRuntimeConfig = {
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
    executor: "node",
    logging: null,
    litestarVersion: "2.18.0",
  } as const

  const createRuntimeConfig = (data: Record<string, unknown>): string => {
    const tmpDir = fs.mkdtempSync(path.join(process.cwd(), "vitest-litestar-"))
    const configPath = path.join(tmpDir, ".litestar.json")
    const merged: Record<string, unknown> = { ...baseRuntimeConfig, ...data }

    const typesOverride = data.types
    if (typesOverride !== undefined) {
      if (typesOverride === null) {
        merged.types = null
      } else if (typeof typesOverride === "object" && typesOverride !== null && !Array.isArray(typesOverride)) {
        merged.types = { ...baseTypesConfig, ...(typesOverride as Record<string, unknown>) }
      } else {
        merged.types = typesOverride
      }
    }

    const loggingOverride = data.logging
    if (loggingOverride !== undefined) {
      if (loggingOverride === null) {
        merged.logging = null
      } else if (typeof loggingOverride === "object" && loggingOverride !== null && !Array.isArray(loggingOverride)) {
        merged.logging = { ...baseLoggingConfig, ...(loggingOverride as Record<string, unknown>) }
      } else {
        merged.logging = loggingOverride
      }
    }

    fs.writeFileSync(configPath, JSON.stringify(merged), "utf-8")
    process.env.LITESTAR_VITE_CONFIG_PATH = configPath
    return configPath
  }

  const cleanupRuntimeConfig = (configPath: string | undefined): void => {
    if (!configPath) return
    try {
      fs.rmSync(path.dirname(configPath), { recursive: true, force: true })
    } catch {
      // ignore
    }
    delete process.env.LITESTAR_VITE_CONFIG_PATH
  }

  it("handles missing configuration", () => {
    /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
    /* @ts-ignore */
    expect(() => litestar()).toThrowError("litestar-vite-plugin: missing configuration.")

    /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
    /* @ts-ignore */
    expect(() => litestar({})).toThrowError('litestar-vite-plugin: missing configuration for "input".')
  })

  it("accepts a single input", () => {
    const plugin = litestar("resources/js/app.ts")[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.build?.rollupOptions?.input).toMatch("resources/js/app.ts")
  })

  it("accepts an array of inputs", () => {
    const plugin = litestar(["resources/js/app.ts", "resources/js/other.js"])[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.build?.rollupOptions?.input).toEqual(["resources/js/app.ts", "resources/js/other.js"])

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.build?.rollupOptions?.input).toEqual(["resources/js/app.ts", "resources/js/other.js"])
  })

  it("accepts a full configuration", () => {
    const plugin = litestar({
      input: "resources/js/app.ts",
      assetUrl: "other-static",
      bundleDir: "other-build",
      ssr: "resources/js/ssr.ts",
      ssrOutDir: "other-ssr-output",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("other-static/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("other-build")
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toBe("other-static/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toBe("other-ssr-output")
    expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.ts")
  })

  it("uses Vite publicDir from python staticDir when provided", () => {
    const configPath = createRuntimeConfig({
      staticDir: "python-public",
    })

    try {
      const plugin = litestar({ input: "resources/js/app.ts" })[0]
      const config = plugin.config({}, { command: "build", mode: "production" })

      expect(config.publicDir).toBe("python-public")
    } finally {
      cleanupRuntimeConfig(configPath)
    }
  })

  it("prefers Vite publicDir over python staticDir", () => {
    const configPath = createRuntimeConfig({
      staticDir: "python-public",
    })

    try {
      const plugin = litestar({ input: "resources/js/app.ts" })[0]
      const config = plugin.config({ publicDir: "user-public" }, { command: "build", mode: "production" })

      expect(config.publicDir).toBe("user-public")
    } finally {
      cleanupRuntimeConfig(configPath)
    }
  })

  it("checks bundleDir for index.html when auto-detecting", async () => {
    const plugin = litestar({
      input: "resources/js/app.ts",
      bundleDir: "custom-dist",
    })[0]

    const accessSpy = vi.spyOn(fs.promises, "access").mockImplementation((p: fs.PathLike) => {
      const file = String(p)
      if (file.endsWith(path.join("custom-dist", "index.html"))) {
        return Promise.resolve()
      }
      if (file.endsWith(path.join("resources", "js", "index.html"))) {
        return Promise.reject(new Error("ENOENT"))
      }
      if (file.endsWith(path.join("index.html"))) {
        return Promise.reject(new Error("ENOENT"))
      }
      return Promise.reject(new Error("ENOENT"))
    })

    // Run config hook to set up plugin state
    plugin.config?.({}, { command: "serve", mode: "development" })

    // Simulate Vite's configResolved hook so envDir is present
    const fakeResolvedConfig = {
      root: process.cwd(),
      envDir: process.cwd(),
      mode: "development",
      base: "/",
      command: "serve",
      server: {},
      build: {},
    }
    plugin.configResolved?.(fakeResolvedConfig as any)

    await (plugin as any).configureServer?.(
      {
        middlewares: { use: vi.fn() },
        config: { root: process.cwd(), envDir: process.cwd(), mode: "development" },
      },
      { command: "serve", mode: "development" },
    )
    expect(accessSpy).toHaveBeenCalled()
  })

  it("respects the users build.manifest config option", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
    })[0]

    const userConfig = { build: { manifest: "my-custom-manifest.json" } }

    const config = plugin.config(userConfig, {
      command: "build",
      mode: "production",
    })

    expect(config.build?.manifest).toBe("my-custom-manifest.json")
  })

  it("has a default manifest path", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
    })[0]

    const userConfig = {}

    const config = plugin.config(userConfig, {
      command: "build",
      mode: "production",
    })

    expect(config.build?.manifest).toBe("manifest.json")
  })

  it("respects users base config option", () => {
    const plugin = litestar({
      input: "resources/js/app.ts",
    })[0]

    const userConfig = { base: "/foo/" }

    const config = plugin.config(userConfig, {
      command: "build",
      mode: "production",
    })

    expect(config.base).toMatch("/foo/")
  })

  it("accepts a partial configuration", () => {
    const plugin = litestar({
      input: "src/js/app.js",
      ssr: "src/js/ssr.js",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toMatch("static/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("public")
    expect(config.build?.rollupOptions?.input).toBe("src/js/app.js")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toMatch("static/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toMatch("src/bootstrap/ssr")
    expect(ssrConfig.build?.rollupOptions?.input).toMatch("src/js/ssr.js")
  })
  it("accepts a partial configuration with an asset URL", () => {
    const plugin = litestar({
      input: "src/js/app.js",
      bundleDir: "/public/build/",
      assetUrl: "/over/the/rainbow/",
      ssr: "src/js/ssr.js",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("/over/the/rainbow/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("public/build")
    expect(config.build?.rollupOptions?.input).toBe("src/js/app.js")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toBe("/over/the/rainbow/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toBe("src/bootstrap/ssr")
    expect(ssrConfig.build?.rollupOptions?.input).toBe("src/js/ssr.js")
  })

  it("uses the default entry point when ssr entry point is not provided", () => {
    // This is support users who may want a dedicated Vite config for SSR.
    const plugin = litestar("resources/js/ssr.js")[0]

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.js")
  })

  it("prefixes the base with ASSET_URL in production mode", () => {
    process.env.ASSET_URL = "http://example.com"
    const plugin = litestar("resources/js/app.js")[0]

    const devConfig = plugin.config({}, { command: "serve", mode: "development" })
    expect(devConfig.base).toBe("/static/")

    const prodConfig = plugin.config({}, { command: "build", mode: "production" })
    expect(prodConfig.base).toBe("http://example.com/")
  })

  it("prevents setting an empty bundleDir", () => {
    expect(
      () =>
        litestar({
          input: "resources/js/app.js",
          bundleDir: "",
        })[0],
    ).toThrowError("bundleDir must be a subdirectory")
  })

  it("handles surrounding slashes on directories", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
      bundleDir: "/build/test/",
      ssrOutDir: "/ssr-output/test/",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("/static/")
    expect(config.build?.outDir).toBe("build/test")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.build?.outDir).toBe("ssr-output/test")
  })

  it("provides an @ alias by default", () => {
    const plugin = litestar("src/js/app.js")[0]

    const config = plugin.config({}, { command: "build", mode: "development" })

    expect(config.resolve?.alias?.["@"]).toBe("/src/")
  })

  it("respects a users existing @ alias", () => {
    const plugin = litestar("src/js/app.js")[0]

    const config = plugin.config(
      {
        resolve: {
          alias: {
            "@": "/somewhere/else",
          },
        },
      },
      { command: "build", mode: "development" },
    )

    expect(config.resolve?.alias?.["@"]).toBe("/somewhere/else")
  })

  it("appends an Alias object when using an alias array", () => {
    const plugin = litestar("src/js/app.js")[0]

    const config = plugin.config(
      {
        resolve: {
          alias: [{ find: "@", replacement: "/something/else" }],
        },
      },
      { command: "build", mode: "development" },
    )

    expect(config.resolve?.alias).toEqual([
      { find: "@", replacement: "/something/else" },
      { find: "@", replacement: "/src/" },
    ])
  })

  it("configures the Vite server when running remotely", () => {
    process.env.VITE_ALLOW_REMOTE = "1"
    const plugin = litestar("resources/js/app.js")[0]

    const config = plugin.config({}, { command: "serve", mode: "development" })
    expect(config.server?.host).toBe("0.0.0.0")
    expect(config.server?.port).toBe(5173)
    expect(config.server?.strictPort).toBe(true)

    process.env.VITE_ALLOW_REMOTE = undefined
  })

  it("allows the Vite port to be configured when running remotely", () => {
    process.env.VITE_ALLOW_REMOTE = "1"
    process.env.VITE_PORT = "1234"
    const plugin = litestar("resources/js/app.js")[0]

    const config = plugin.config({}, { command: "serve", mode: "development" })
    expect(config.server?.host).toBe("0.0.0.0")
    expect(config.server?.port).toBe(1234)
    expect(config.server?.strictPort).toBe(true)
  })

  it("allows the server configuration to be overridden inside a container", () => {
    process.env.VITE_ALLOW_REMOTE = "1"
    const plugin = litestar("resources/js/app.js")[0]

    const config = plugin.config(
      {
        server: {
          host: "example.com",
          port: 1234,
          strictPort: false,
        },
      },
      { command: "serve", mode: "development" },
    )
    expect(config.server?.host).toBe("example.com")
    expect(config.server?.port).toBe(1234)
    expect(config.server?.strictPort).toBe(false)
  })

  it("prevents the Inertia helpers from being externalized", () => {
    /* eslint-disable @typescript-eslint/ban-ts-comment */
    const plugin = litestar("resources/js/app.js")[0]

    const noSsrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    /* @ts-ignore */
    expect(noSsrConfig.ssr.noExternal).toEqual(["litestar-vite-plugin"])

    /* @ts-ignore */
    const nothingExternalConfig = plugin.config({ ssr: { noExternal: true }, build: { ssr: true } }, { command: "build", mode: "production" })
    /* @ts-ignore */
    expect(nothingExternalConfig.ssr.noExternal).toBe(true)

    /* @ts-ignore */
    const arrayNoExternalConfig = plugin.config({ ssr: { noExternal: ["foo"] }, build: { ssr: true } }, { command: "build", mode: "production" })
    /* @ts-ignore */
    expect(arrayNoExternalConfig.ssr.noExternal).toEqual(["foo", "litestar-vite-plugin"])

    /* @ts-ignore */
    const stringNoExternalConfig = plugin.config({ ssr: { noExternal: "foo" }, build: { ssr: true } }, { command: "build", mode: "production" })
    /* @ts-ignore */
    expect(stringNoExternalConfig.ssr.noExternal).toEqual(["foo", "litestar-vite-plugin"])
  })

  it("does not configure full reload when configuration it not an object", () => {
    const plugins = litestar("resources/js/app.js")

    // With auto mode, types are disabled when no .litestar.json exists
    expect(plugins.length).toBe(1) // main plugin only (types disabled in auto mode without .litestar.json)
  })

  it("does not configure full reload when refresh is not present", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      types: false,
    })

    expect(plugins.length).toBe(1)
  })

  it("does not configure full reload when refresh is set to undefined", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: undefined,
      types: false,
    })
    expect(plugins.length).toBe(1)
  })

  it("does not configure full reload when refresh is false", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: false,
      types: false,
    })

    expect(plugins.length).toBe(1)
  })

  it("configures full reload with python and template files when refresh is true", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: true,
      types: false,
    })

    expect(plugins.length).toBe(2)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["src/**", "resources/**", "assets/**"],
    })
  })

  it("configures full reload when refresh is a single path", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: "path/to/watch/**",
      types: false,
    })

    expect(plugins.length).toBe(2)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["path/to/watch/**"],
    })
  })

  it("configures full reload when refresh is an array of paths", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: ["path/to/watch/**", "another/to/watch/**"],
      types: false,
    })

    expect(plugins.length).toBe(2)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["path/to/watch/**", "another/to/watch/**"],
    })
  })

  it("configures full reload when refresh is a complete configuration to proxy", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: {
        paths: ["path/to/watch/**", "another/to/watch/**"],
        config: { delay: 987 },
      },
      types: false,
    })

    expect(plugins.length).toBe(2)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["path/to/watch/**", "another/to/watch/**"],
      config: { delay: 987 },
    })
  })

  it("configures full reload when refresh is an array of complete configurations to proxy", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: [
        {
          paths: ["path/to/watch/**"],
          config: { delay: 987 },
        },
        {
          paths: ["another/to/watch/**"],
          config: { delay: 123 },
        },
      ],
      types: false,
    })

    expect(plugins.length).toBe(3)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["path/to/watch/**"],
      config: { delay: 987 },
    })
    /** @ts-ignore */
    expect(plugins[2].__litestar_plugin_config).toEqual({
      paths: ["another/to/watch/**"],
      config: { delay: 123 },
    })
  })

  it("handles TLS configuration", () => {
    process.env.VITE_SERVER_KEY = "path/to/key"
    process.env.VITE_SERVER_CERT = "path/to/cert"
    process.env.APP_URL = "https://example.com"

    const plugin = litestar("resources/js/app.js")[0]

    expect(() => plugin.config({}, { command: "serve", mode: "development" })).toThrow(/Unable to find the certificate files/)
  })

  it("handles invalid APP_URL", () => {
    process.env.VITE_SERVER_KEY = "path/to/key"
    process.env.VITE_SERVER_CERT = "path/to/cert"
    process.env.APP_URL = "invalid-url"

    const plugin = litestar("resources/js/app.js")[0]

    expect(() => plugin.config({}, { command: "serve", mode: "development" })).toThrow(/Unable to find the certificate files specified in your environment/)
  })

  it("handles missing config directory", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
      detectTls: true,
    })[0]

    expect(() => plugin.config({}, { command: "serve", mode: "development" })).toThrow(/Unable to find the configuration file/)
  })

  describe("HTML file serving", () => {
    let mockServer: any
    let mockMiddleware: any
    let mockRes: any
    let mockNext: any
    let plugin: any
    let serverHook: any
    const testRootDir = "/test/root"
    const testResourceDir = "resources"
    const testPublicDir = "public"

    const rootIndexPath = path.join(testRootDir, "index.html")
    const resourceIndexPath = path.join(testRootDir, testResourceDir, "index.html")
    const publicIndexPath = path.join(testRootDir, testPublicDir, "index.html")
    // Use original placeholder path logic (built file from dev-server/)
    const _placeholderPath = path.resolve(__dirname, "..", "..", "..", "dist", "js", "dev-server-index.html")

    beforeEach(() => {
      vi.clearAllMocks()
    })

    const setupServer = async (pluginOptions = {}, serverConfig = {}) => {
      mockServer = {
        config: {
          root: testRootDir,
          envDir: process.cwd(),
          mode: "development",
          base: "/",
          server: {
            origin: "http://localhost:5173",
          },
          logger: { info: vi.fn(), error: vi.fn() },
          ...serverConfig,
        },
        transformIndexHtml: vi.fn().mockImplementation(async (_url, html) => `<html>transformed ${html}</html>`),
        middlewares: {
          use: vi.fn().mockImplementation((middleware) => {
            mockMiddleware = middleware
          }),
        },
      }
      mockRes = {
        statusCode: 0,
        setHeader: vi.fn(),
        end: vi.fn(),
      }
      mockNext = vi.fn()

      plugin = litestar({
        input: "resources/js/app.js",
        resourceDir: testResourceDir,
        autoDetectIndex: true,
        ...pluginOptions,
      })[0]

      plugin.configResolved?.(mockServer.config)

      const hookResult = await plugin.configureServer?.(mockServer)
      serverHook = typeof hookResult === "function" ? hookResult : hookResult?.()

      if (typeof serverHook === "function") {
        serverHook()
      }
    }

    const mockFs = (foundPath: string | null) => {
      // Only mock access here
      vi.spyOn(fs.promises, "access").mockImplementation(async (p) => {
        if (p === foundPath) return undefined
        throw new Error("File not found")
      })
    }

    it("serves index.html from root when detected", async () => {
      await setupServer()
      mockFs(rootIndexPath)
      vi.spyOn(fs.promises, "readFile").mockResolvedValue("<html>root</html>")
      await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockServer.transformIndexHtml).toHaveBeenCalledWith("/", "<html>root</html>", "/")
      expect(mockRes.end).toHaveBeenCalledWith("<html>transformed <html>root</html></html>")
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves index.html from resource directory when detected", async () => {
      await setupServer()
      mockFs(resourceIndexPath)
      vi.spyOn(fs.promises, "readFile").mockResolvedValue("<html>resource</html>")
      await mockMiddleware({ url: "/index.html", originalUrl: "/index.html" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockServer.transformIndexHtml).toHaveBeenCalledWith("/index.html", "<html>resource</html>", "/index.html")
      expect(mockRes.end).toHaveBeenCalledWith("<html>transformed <html>resource</html></html>")
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves index.html from public directory when detected", async () => {
      await setupServer()
      mockFs(publicIndexPath)
      vi.spyOn(fs.promises, "readFile").mockResolvedValue("<html>public</html>")
      await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockServer.transformIndexHtml).toHaveBeenCalledWith("/", "<html>public</html>", "/")
      expect(mockRes.end).toHaveBeenCalledWith("<html>transformed <html>public</html></html>")
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves placeholder when index.html is not detected and url is /index.html", async () => {
      const appUrl = "http://test.app"
      process.env.APP_URL = appUrl // Set env BEFORE setupServer
      await setupServer()
      mockFs(null)
      // No specific readFile mock needed, relies on actual file read via robust dirname

      await mockMiddleware({ url: "/index.html", originalUrl: "/index.html" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      // Expect actual content with replaced URL
      expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
      expect(mockServer.transformIndexHtml).not.toHaveBeenCalled()
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves placeholder when index.html is not detected and url is /", async () => {
      // When no index.html exists (hybrid/inertia mode), serve the placeholder at root
      // This helps users who accidentally navigate to the Vite dev server port
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl
      await setupServer()
      mockFs(null)

      await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("calls next() for non-root and non-/index.html requests", async () => {
      await setupServer()
      mockFs(rootIndexPath)

      await mockMiddleware({ url: "/other/path", originalUrl: "/other/path" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(0)
      expect(mockRes.setHeader).not.toHaveBeenCalled()
      expect(mockRes.end).not.toHaveBeenCalled()
      expect(mockNext).toHaveBeenCalledTimes(1)
    })

    it("serves placeholder for / when autoDetectIndex is false, even if index exists", async () => {
      // When autoDetectIndex is false, we don't look for index.html
      // So we serve the placeholder to guide users to the backend URL
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl
      await setupServer({ autoDetectIndex: false })
      mockFs(rootIndexPath)

      await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves placeholder for /index.html when autoDetectIndex is false", async () => {
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl // Set env BEFORE setupServer
      await setupServer({ autoDetectIndex: false })
      mockFs(null)
      // No specific readFile mock needed, relies on actual file read via robust dirname

      await mockMiddleware({ url: "/index.html", originalUrl: "/index.html" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      // Expect actual content with replaced URL
      expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves placeholder when mode is 'hybrid' in .litestar.json (inertiaMode auto-detected)", async () => {
      // When Python sets mode="inertia", it's normalized to "hybrid" in .litestar.json.
      // In inertia mode, the Vite dev server should always show the placeholder page.
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl
      const configPath = createRuntimeConfig({ mode: "hybrid" })

      try {
        await setupServer() // No explicit inertiaMode - should auto-detect from .litestar.json
        mockFs(rootIndexPath) // index.html exists

        await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

        // Should serve placeholder even if index.html exists
        expect(mockRes.statusCode).toBe(200)
        expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
        expect(mockServer.transformIndexHtml).not.toHaveBeenCalled()
        expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
        expect(mockNext).not.toHaveBeenCalled()
      } finally {
        cleanupRuntimeConfig(configPath)
      }
    })

    it("serves placeholder when mode is 'inertia' in .litestar.json", async () => {
      // In inertia mode, the Vite dev server should always show the placeholder page.
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl
      const configPath = createRuntimeConfig({ mode: "inertia" })

      try {
        await setupServer()
        mockFs(rootIndexPath) // index.html exists

        await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

        // Should serve placeholder even if index.html exists
        expect(mockRes.statusCode).toBe(200)
        expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
        expect(mockServer.transformIndexHtml).not.toHaveBeenCalled()
        expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
        expect(mockNext).not.toHaveBeenCalled()
      } finally {
        cleanupRuntimeConfig(configPath)
      }
    })

    it("serves placeholder for /index.html when inertia mode is enabled, even if index exists", async () => {
      const appUrl = "http://test.app:8000"
      process.env.APP_URL = appUrl
      const configPath = createRuntimeConfig({ mode: "inertia" })

      try {
        await setupServer()
        mockFs(rootIndexPath) // index.html exists

        await mockMiddleware({ url: "/index.html", originalUrl: "/index.html" }, mockRes, mockNext)

        expect(mockRes.statusCode).toBe(200)
        expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
        expect(mockServer.transformIndexHtml).not.toHaveBeenCalled()
        expect(mockRes.end).toHaveBeenCalledWith(actualPlaceholderContent.replace(/{{ APP_URL }}/g, appUrl))
        expect(mockNext).not.toHaveBeenCalled()
      } finally {
        cleanupRuntimeConfig(configPath)
      }
    })

    it("handles errors during index.html reading", async () => {
      await setupServer()
      mockFs(rootIndexPath) // Access mock allows finding the path
      // No specific readFile mock needed, let actual read fail

      await mockMiddleware({ url: "/", originalUrl: "/" }, mockRes, mockNext)

      // Check for any error and specific code
      expect(mockNext).toHaveBeenCalledWith(expect.any(Error))
      expect(mockNext.mock.calls[0][0].code).toBe("ENOENT")
      expect(mockRes.end).not.toHaveBeenCalled()
      expect(mockServer.config.logger.error).toHaveBeenCalledWith(expect.stringContaining("Error serving index.html"))
    })

    it("handles errors during placeholder reading", async () => {
      await setupServer()
      mockFs(null) // Access mock prevents finding a path
      const placeholderError = new Error("Cannot read placeholder")
      // Specific mock to force placeholder read error
      vi.spyOn(fs.promises, "readFile").mockRejectedValue(placeholderError)

      await mockMiddleware({ url: "/index.html", originalUrl: "/index.html" }, mockRes, mockNext)

      expect(mockRes.statusCode).toBe(404)
      expect(mockRes.end).toHaveBeenCalledWith(expect.stringContaining("Error loading placeholder"))
      expect(mockNext).not.toHaveBeenCalled()
      expect(mockServer.config.logger.error).toHaveBeenCalledWith(expect.stringContaining("Error serving placeholder index.html"))
    })
  })
})

describe("type generation config detection", () => {
  const originalEnv = { ...process.env }
  let tempDir: string

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(process.cwd(), "vitest-config-detect-"))
    process.env = { ...originalEnv }
  })

  afterEach(() => {
    process.env = { ...originalEnv }
    try {
      fs.rmSync(tempDir, { recursive: true, force: true })
    } catch {
      // ignore
    }
  })

  it("prefers openapi-ts.config.ts over hey-api.config.ts", () => {
    // Create both config files
    fs.writeFileSync(path.join(tempDir, "openapi-ts.config.ts"), "export default {}")
    fs.writeFileSync(path.join(tempDir, "hey-api.config.ts"), "export default {}")

    // Check detection order
    const candidates = [path.resolve(tempDir, "openapi-ts.config.ts"), path.resolve(tempDir, "hey-api.config.ts"), path.resolve(tempDir, ".hey-api.config.ts")]
    const configPath = candidates.find((p) => fs.existsSync(p)) || null

    expect(configPath).toBe(path.resolve(tempDir, "openapi-ts.config.ts"))
  })

  it("falls back to hey-api.config.ts when openapi-ts.config.ts missing", () => {
    // Create only hey-api config
    fs.writeFileSync(path.join(tempDir, "hey-api.config.ts"), "export default {}")

    const candidates = [path.resolve(tempDir, "openapi-ts.config.ts"), path.resolve(tempDir, "hey-api.config.ts"), path.resolve(tempDir, ".hey-api.config.ts")]
    const configPath = candidates.find((p) => fs.existsSync(p)) || null

    expect(configPath).toBe(path.resolve(tempDir, "hey-api.config.ts"))
  })

  it("falls back to .hey-api.config.ts (dotfile) when others missing", () => {
    // Create only the dotfile variant
    fs.writeFileSync(path.join(tempDir, ".hey-api.config.ts"), "export default {}")

    const candidates = [path.resolve(tempDir, "openapi-ts.config.ts"), path.resolve(tempDir, "hey-api.config.ts"), path.resolve(tempDir, ".hey-api.config.ts")]
    const configPath = candidates.find((p) => fs.existsSync(p)) || null

    expect(configPath).toBe(path.resolve(tempDir, ".hey-api.config.ts"))
  })

  it("returns null when no config file exists", () => {
    // Create empty directory - no config files
    const candidates = [path.resolve(tempDir, "openapi-ts.config.ts"), path.resolve(tempDir, "hey-api.config.ts"), path.resolve(tempDir, ".hey-api.config.ts")]
    const configPath = candidates.find((p) => fs.existsSync(p)) || null

    expect(configPath).toBeNull()
  })
})

describe("inertia-helpers", () => {
  const testPath = "./__data__/dummy.ts"

  beforeEach(() => {
    vi.resetModules()
    vi.mock("./__data__/dummy.ts", () => ({
      default: "Dummy File",
    }))
  })

  it("pass glob value to resolvePageComponent", async () => {
    const pages = {
      [testPath]: Promise.resolve({ default: "Dummy File" }),
    }

    const file = await resolvePageComponent<{ default: string }>(testPath, pages)
    expect(file.default).toBe("Dummy File")
  })

  it("pass eagerly globed value to resolvePageComponent", async () => {
    const pages = {
      [testPath]: { default: "Dummy File" },
    }
    const file = await resolvePageComponent<{ default: string }>(testPath, pages as any)
    expect(file.default).toBe("Dummy File")
  })

  it("accepts array of paths", async () => {
    const pages = {
      [testPath]: { default: "Dummy File" },
    }
    const file = await resolvePageComponent<{ default: string }>(["missing-page", testPath], pages as any)
    expect(file.default).toBe("Dummy File")
  })

  it("throws an error when a page is not found", async () => {
    const pages = {}
    await expect(resolvePageComponent<{ default: string }>("missing-page", pages)).rejects.toThrow("Page not found: missing-page")
  })

  // Note: Route utility tests removed - use generated routes.ts instead
  // See: import { route, routes } from '@/generated/routes'
})
