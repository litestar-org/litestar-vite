import fs from "node:fs"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import litestar from "../src"
import { getRelativeUrlPath, isCurrentRoute, isRoute, resolvePageComponent, route, toRoute } from "../src/inertia-helpers"

// Mock the fs module
vi.mock("fs", async () => {
  const actual = await vi.importActual<typeof import("fs")>("fs")

  return {
    default: {
      ...actual,
      existsSync: (path: string) => ["resources/", "assets/", "src/"].includes(path) || actual.existsSync(path),
    },
  }
})
// Mock process.env
const originalEnv = process.env
beforeEach(() => {
  vi.resetModules()
  process.env = { ...originalEnv }
})

afterEach(() => {
  process.env = originalEnv
  vi.clearAllMocks()
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
      bundleDirectory: "other-build",
      ssr: "resources/js/ssr.ts",
      ssrOutputDirectory: "other-ssr-output",
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
      input: "resources/js/app.js",
      ssr: "resources/js/ssr.js",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toMatch("static/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("public")
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.js")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toMatch("static/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toMatch("resources/bootstrap/ssr")
    expect(ssrConfig.build?.rollupOptions?.input).toMatch("resources/js/ssr.js")
  })
  it("accepts a partial configuration with an asset URL", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
      bundleDirectory: "/public/build/",
      assetUrl: "/over/the/rainbow/",
      ssr: "resources/js/ssr.js",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("/over/the/rainbow/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("public/build")
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.js")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toBe("/over/the/rainbow/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toBe("resources/bootstrap/ssr")
    expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.js")
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
    expect(devConfig.base).toBe("static")

    const prodConfig = plugin.config({}, { command: "build", mode: "production" })
    expect(prodConfig.base).toBe("http://example.com/")
  })

  it("prevents setting an empty bundleDirectory", () => {
    expect(
      () =>
        litestar({
          input: "resources/js/app.js",
          bundleDirectory: "",
        })[0],
    ).toThrowError("bundleDirectory must be a subdirectory")
  })

  it("handles surrounding slashes on directories", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
      bundleDirectory: "/build/test/",
      ssrOutputDirectory: "/ssr-output/test/",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("static/")
    expect(config.build?.outDir).toBe("build/test")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.build?.outDir).toBe("ssr-output/test")
  })

  it("provides an @ alias by default", () => {
    const plugin = litestar("resources/js/app.js")[0]

    const config = plugin.config({}, { command: "build", mode: "development" })

    expect(config.resolve?.alias?.["@"]).toBe("/resources/")
  })

  it("respects a users existing @ alias", () => {
    const plugin = litestar("resources/js/app.js")[0]

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
    const plugin = litestar("resources/js/app.js")[0]

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
      { find: "@", replacement: "/resources/" },
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

    expect(plugins.length).toBe(1)
  })

  it("does not configure full reload when refresh is not present", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
    })

    expect(plugins.length).toBe(1)
  })

  it("does not configure full reload when refresh is set to undefined", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: undefined,
    })
    expect(plugins.length).toBe(1)
  })

  it("does not configure full reload when refresh is false", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: false,
    })

    expect(plugins.length).toBe(1)
  })

  it("configures full reload with python and template files when refresh is true", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: true,
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

    beforeEach(() => {
      // Mock Vite dev server with complete config
      mockServer = {
        config: {
          root: "/test/root",
          envDir: process.cwd(),
          mode: "development",
          base: "/",
          server: {
            origin: "http://localhost:5173",
          },
        },
        transformIndexHtml: vi.fn().mockResolvedValue("<html>transformed</html>"),
        middlewares: {
          use: vi.fn().mockImplementation((middleware) => {
            mockMiddleware = middleware
          }),
        },
      }

      // Mock response object
      mockRes = {
        statusCode: 0,
        setHeader: vi.fn(),
        end: vi.fn(),
      }

      // Mock next function
      mockNext = vi.fn()

      // Mock fs promises
      vi.spyOn(fs.promises, "access").mockResolvedValue(undefined)
      vi.spyOn(fs.promises, "readFile").mockResolvedValue("<html>test</html>")

      // Initialize plugin and call configResolved
      plugin = litestar({
        input: "resources/js/app.js",
        resourceDirectory: "resources",
      })[0]

      // Call configResolved to set up resolvedConfig
      plugin.configResolved?.(mockServer.config)
    })

    it("serves index.html when detected", async () => {
      // Mock findIndexHtmlPath to return a path
      vi.spyOn(fs.promises, "access").mockResolvedValueOnce(undefined)

      // Configure the server
      const serverHook = await plugin.configureServer?.(mockServer)
      // @ts-ignore - Server hook can be a function or object with handler
      if (serverHook && typeof serverHook === "function") {
        await serverHook()
      }

      // Call the middleware with root path
      await mockMiddleware(
        {
          url: "/",
          originalUrl: "/",
        },
        mockRes,
        mockNext,
      )

      // Verify the response
      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockRes.end).toHaveBeenCalledWith("<html>transformed</html>")
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("serves placeholder when index.html is not detected", async () => {
      // Mock findIndexHtmlPath to return null
      vi.spyOn(fs.promises, "access").mockRejectedValueOnce(new Error("File not found"))

      // Mock the placeholder file read
      const placeholderContent = `<html>
        <head>
          <title>Litestar Vite</title>
        </head>
        <body>
          <div id="app"></div>
        </body>
      </html>`

      // Mock transformIndexHtml to only transform non-placeholder content
      mockServer.transformIndexHtml = vi.fn().mockImplementation((url, html) => {
        if (html.includes("Litestar Vite")) {
          return html // Don't transform placeholder content
        }
        return "<html>transformed</html>" // Transform other content
      })

      vi.spyOn(fs.promises, "readFile").mockResolvedValueOnce(placeholderContent)

      // Configure the server
      const serverHook = await plugin.configureServer?.(mockServer)
      // @ts-ignore - Server hook can be a function or object with handler
      if (serverHook && typeof serverHook === "function") {
        await serverHook()
      }

      // Call the middleware with /index.html path
      await mockMiddleware(
        {
          url: "/index.html",
          originalUrl: "/index.html",
        },
        mockRes,
        mockNext,
      )

      // Verify the response
      expect(mockRes.statusCode).toBe(200)
      expect(mockRes.setHeader).toHaveBeenCalledWith("Content-Type", "text/html")
      expect(mockRes.end).toHaveBeenCalledWith(expect.stringContaining("Litestar Vite"))
      expect(mockNext).not.toHaveBeenCalled()
    })

    it("passes through non-index.html requests", async () => {
      // Configure the server
      const serverHook = await plugin.configureServer?.(mockServer)
      // @ts-ignore - Server hook can be a function or object with handler
      if (serverHook && typeof serverHook === "function") {
        await serverHook()
      }

      // Call the middleware with a non-index path
      await mockMiddleware(
        {
          url: "/other",
          originalUrl: "/other",
        },
        mockRes,
        mockNext,
      )

      // Verify the request was passed through
      expect(mockRes.statusCode).toBe(0)
      expect(mockRes.setHeader).not.toHaveBeenCalled()
      expect(mockRes.end).not.toHaveBeenCalled()
      expect(mockNext).toHaveBeenCalled()
    })
  })
})
describe("inertia-helpers", () => {
  const testPath = "./__data__/dummy.ts"

  beforeEach(() => {
    vi.resetModules()
    // Mock the import.meta.glob functionality
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
    // @ts-ignore
    const file = await resolvePageComponent<{ default: string }>(testPath, pages)
    expect(file.default).toBe("Dummy File")
  })

  it("accepts array of paths", async () => {
    const pages = {
      [testPath]: { default: "Dummy File" },
    }

    const file = await resolvePageComponent<{ default: string }>(
      ["missing-page", testPath],
      // @ts-ignore
      pages,
    )
    expect(file.default).toBe("Dummy File")
  })

  it("throws an error when a page is not found", async () => {
    const pages = {}
    await expect(resolvePageComponent<{ default: string }>("missing-page", pages)).rejects.toThrow("Page not found: missing-page")
  })

  describe("route() edge cases", () => {
    it("handles missing route names", () => {
      expect(route("non-existent-route")).toBe("#")
    })

    it("handles array arguments", () => {
      const result = route("users:get", ["123e4567-e89b-12d3-a456-426614174000"])
      expect(result).toContain("/api/users/get/123e4567-e89b-12d3-a456-426614174000")
    })

    it("handles wrong number of arguments", () => {
      expect(route("users:get", [])).toBe("#")
    })

    it("handles missing arguments in object", () => {
      expect(route("users:get", { wrong_id: "123" })).toBe("#")
    })
  })

  describe("getRelativeUrlPath()", () => {
    it("handles invalid URLs", () => {
      expect(getRelativeUrlPath("invalid-url")).toBe("invalid-url")
    })

    it("preserves query parameters and hash", () => {
      expect(getRelativeUrlPath("http://example.com/path?query=1#hash")).toBe("/path?query=1#hash")
    })
  })

  describe("toRoute()", () => {
    it("handles root path", () => {
      expect(toRoute("/")).toBe("home")
    })

    it("handles UUID parameters", () => {
      expect(toRoute("/api/users/get/123e4567-e89b-12d3-a456-426614174000")).toBe("users:get")
    })

    it("handles path parameters", () => {
      expect(toRoute("/saq/static/some/deep/path")).toBe("saq")
    })

    it("handles non-matching routes", () => {
      expect(toRoute("/non-existent")).toBe(null)
    })

    it("handles trailing slashes", () => {
      expect(toRoute("/api/users/list/")).toBe("users:list")
    })
  })

  describe("currentRoute()", () => {
    beforeEach(() => {
      // Mock window.location
      Object.defineProperty(window, "location", {
        value: {
          pathname: "/api/users/list",
        },
        writable: true,
      })
    })

    it("returns current route name", () => {
      expect(currentRoute()).toBe("users:list")
    })

    it("returns null for non-matching routes", () => {
      window.location.pathname = "/non-existent"
      expect(currentRoute()).toBe(null)
    })
  })

  describe("isRoute()", () => {
    it("matches exact routes", () => {
      expect(isRoute("/api/users/list", "users:list")).toBe(true)
    })

    it("matches routes with parameters", () => {
      expect(isRoute("/api/users/get/123e4567-e89b-12d3-a456-426614174000", "users:*")).toBe(true)
    })

    it("handles non-matching routes", () => {
      expect(isRoute("/non-existent", "users:*")).toBe(false)
    })

    it("matches routes with path parameters", () => {
      expect(isRoute("/saq/static/deep/nested/path", "saq")).toBe(true)
    })
  })

  describe("isCurrentRoute()", () => {
    beforeEach(() => {
      // Mock window.location
      Object.defineProperty(window, "location", {
        value: {
          pathname: "/api/users/list",
        },
        writable: true,
      })
    })

    it("matches current route with pattern", () => {
      expect(isCurrentRoute("users:*")).toBe(true)
    })

    it("handles exact matches", () => {
      expect(isCurrentRoute("users:list")).toBe(true)
    })

    it("handles non-matching routes", () => {
      expect(isCurrentRoute("teams:*")).toBe(false)
    })

    it("handles invalid current route", () => {
      window.location.pathname = "/non-existent"
      expect(isCurrentRoute("users:*")).toBe(false)
    })
  })
})
