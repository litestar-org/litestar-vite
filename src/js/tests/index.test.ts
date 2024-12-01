import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import litestar from "../src"
import { currentRoute, getRelativeUrlPath, isCurrentRoute, isRoute, resolvePageComponent, route, toRoute } from "../src/inertia-helpers"

describe("litestar-vite-plugin", () => {
  const originalEnv = { ...process.env }

  afterEach(() => {
    process.env = { ...originalEnv }
    vi.clearAllMocks()
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
    expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/app.ts")
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
      assetUrl: "other-build",
      bundleDirectory: "other-build",
      ssr: "resources/js/ssr.ts",
      ssrOutputDirectory: "other-ssr-output",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("other-build/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("other-build")
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.ts")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toBe("other-build/")
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

    expect(config.base).toBe("/foo/")
  })

  it("accepts a partial configuration", () => {
    const plugin = litestar({
      input: "resources/js/app.js",
      ssr: "resources/js/ssr.js",
    })[0]

    const config = plugin.config({}, { command: "build", mode: "production" })
    expect(config.base).toBe("static/")
    expect(config.build?.manifest).toBe("manifest.json")
    expect(config.build?.outDir).toBe("public")
    expect(config.build?.rollupOptions?.input).toBe("resources/js/app.js")

    const ssrConfig = plugin.config({ build: { ssr: true } }, { command: "build", mode: "production" })
    expect(ssrConfig.base).toBe("static/")
    expect(ssrConfig.build?.manifest).toBe(false)
    expect(ssrConfig.build?.outDir).toBe("resources/bootstrap/ssr")
    expect(ssrConfig.build?.rollupOptions?.input).toBe("resources/js/ssr.js")
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

  it("configures the Vite server when running remotely or in a container", () => {
    process.env.VITE_ALLOW_REMOTE = "1"
    const plugin = litestar("resources/js/app.js")[0]

    const config = plugin.config({}, { command: "serve", mode: "development" })
    expect(config.server?.host).toBe("0.0.0.0")
    expect(config.server?.port).toBe(5173)
    expect(config.server?.strictPort).toBe(true)
  })

  it("allows the Vite port to be configured when inside a container", () => {
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

  it("configures full reload with routes and views when refresh is true", () => {
    const plugins = litestar({
      input: "resources/js/app.js",
      refresh: true,
    })

    expect(plugins.length).toBe(2)
    /** @ts-ignore */
    expect(plugins[1].__litestar_plugin_config).toEqual({
      paths: ["**/*.py", "**/*.j2", "**/*.html.j2", "**/*.html", "**/assets/**/*"],
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
})

describe("inertia-helpers", () => {
  const path = "./__data__/dummy.ts"
  it("pass glob value to resolvePageComponent", async () => {
    const file = await resolvePageComponent<{ default: string }>(
      path,
      /* @ts-ignore */
      import.meta.glob("./__data__/*.ts"),
    )
    expect(file.default).toBe("Dummy File")
  })

  it("pass eagerly globed value to resolvePageComponent", async () => {
    const file = await resolvePageComponent<{ default: string }>(
      path,
      /* @ts-ignore */
      import.meta.glob("./__data__/*.ts", { eager: true }),
    )
    expect(file.default).toBe("Dummy File")
  })

  it("accepts array of paths", async () => {
    const file = await resolvePageComponent<{ default: string }>(
      ["missing-page", path],
      /* @ts-ignore */
      import.meta.glob("./__data__/*.ts", { eager: true }),
      /* @ts-ignore */
      path,
    )
    expect(file.default).toBe("Dummy File")
  })

  it("throws an error when a page is not found", async () => {
    const callback = () =>
      resolvePageComponent<{ default: string }>(
        "missing-page",
        /* @ts-ignore */
        import.meta.glob("./__data__/*.ts"),
      )
    await expect(callback).rejects.toThrowError(new Error("Page not found: missing-page"))
  })

  it("throws an error when a page is not found", async () => {
    const callback = () =>
      resolvePageComponent<{ default: string }>(
        ["missing-page-1", "missing-page-2"],
        /* @ts-ignore */
        import.meta.glob("./__data__/*.ts"),
      )
    await expect(callback).rejects.toThrowError(new Error("Page not found: missing-page-1,missing-page-2"))
  })
})

describe("route helpers", () => {
  beforeEach(() => {
    // Setup mock routes based on the provided JSON
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

  describe("route()", () => {
    it("generates URLs from route names with named parameters", () => {
      expect(route("users:get", { user_id: "123e4567-e89b-12d3-a456-426614174000" })).toContain("/api/users/get/123e4567-e89b-12d3-a456-426614174000")

      expect(route("worker:queue-detail", { queue_id: "default" })).toContain("/saq/api/queues/default")
    })

    it('returns "#" for invalid routes', () => {
      expect(route("invalid.route")).toBe("#")
    })

    it("handles missing parameters", () => {
      expect(route("users:get")).toBe("#")
    })
  })

  describe("getRelativeUrlPath()", () => {
    it("extracts relative path from full URL", () => {
      expect(getRelativeUrlPath("http://example.com/api/users/get/123e4567-e89b-12d3-a456-426614174000?page=1#section")).toBe(
        "/api/users/get/123e4567-e89b-12d3-a456-426614174000?page=1#section",
      )
    })

    it("returns original string for relative paths", () => {
      expect(getRelativeUrlPath("/api/users/get/123e4567-e89b-12d3-a456-426614174000")).toBe("/api/users/get/123e4567-e89b-12d3-a456-426614174000")
    })
  })

  describe("toRoute()", () => {
    it("matches URLs to route names", () => {
      expect(toRoute("/api/users/list")).toBe("users:list")
      expect(toRoute("/api/users/get/123e4567-e89b-12d3-a456-426614174000")).toBe("users:get")
      expect(toRoute("/teams/list")).toBe("teams.list")
      expect(toRoute("/teams/show/123e4567-e89b-12d3-a456-426614174000")).toBe("teams.show")
      expect(toRoute("/saq/api/queues/list")).toBe("worker:queue-list")
      expect(toRoute("/saq/api/queues/default/jobs/123")).toBe("worker:job-detail")
      expect(toRoute("/saq/static/path/to/file.pdf")).toBe("saq")
    })

    it("returns null for unmatched routes", () => {
      expect(toRoute("/not/a/real/route")).toBeNull()
    })
  })

  describe("currentRoute()", () => {
    it("returns current route name based on window location", () => {
      // Mock window.location
      Object.defineProperty(window, "location", {
        value: { pathname: "/api/users/get/123e4567-e89b-12d3-a456-426614174000" },
        writable: true,
      })

      expect(currentRoute()).toBe("users:get")
    })

    it("returns null when current location does not match any route", () => {
      Object.defineProperty(window, "location", {
        value: { pathname: "/not/a/real/route" },
        writable: true,
      })

      expect(currentRoute()).toBeNull()
    })
  })

  describe("isRoute()", () => {
    it("checks if URL matches route pattern", () => {
      expect(isRoute("/api/users/get/123e4567-e89b-12d3-a456-426614174000", "users:get")).toBe(true)
      expect(isRoute("/invalid/path", "users:get")).toBe(false)
    })
  })

  describe("isCurrentRoute()", () => {
    it("checks if current location matches route pattern", () => {
      Object.defineProperty(window, "location", {
        value: { pathname: "/api/users/get/123e4567-e89b-12d3-a456-426614174000" },
        writable: true,
      })

      expect(isCurrentRoute("users:get")).toBe(true)
      expect(isCurrentRoute("users.*")).toBe(true)
    })

    it("returns false when current location does not match route pattern", () => {
      Object.defineProperty(window, "location", {
        value: { pathname: "/not/a/real/route" },
        writable: true,
      })

      expect(isCurrentRoute("users:get")).toBe(false)
    })
  })
})
