import fs from "node:fs"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import litestarAstro from "../../src/astro"
import litestarNuxtModule from "../../src/nuxt"
import { litestarSvelteKit } from "../../src/sveltekit"

interface TestServer {
  close: ReturnType<typeof vi.fn>
  middlewares: { use: ReturnType<typeof vi.fn> }
}

function createServer(): TestServer {
  return {
    close: vi.fn().mockResolvedValue(undefined),
    middlewares: { use: vi.fn() },
  }
}

function expectManagedShutdownInstalled(): void {
  expect(process.stdin.on).toHaveBeenCalledWith("end", expect.any(Function))
  expect(process.stdin.on).toHaveBeenCalledWith("close", expect.any(Function))
  expect(process.stdin.resume).toHaveBeenCalledOnce()
}

describe("framework-managed shutdown integration", () => {
  beforeEach(() => {
    process.env.LITESTAR_VITE_MANAGED = "1"
    delete process.env.LITESTAR_VITE_CONFIG_PATH
    vi.spyOn(fs, "existsSync").mockReturnValue(false)
    vi.spyOn(fs, "writeFileSync").mockImplementation(() => undefined)
    vi.spyOn(fs, "mkdirSync").mockImplementation(() => undefined)
    vi.spyOn(process.stdin, "on").mockImplementation(() => process.stdin)
    vi.spyOn(process.stdin, "resume").mockImplementation(() => process.stdin)
  })

  afterEach(() => {
    delete process.env.LITESTAR_VITE_MANAGED
    vi.restoreAllMocks()
  })

  it("installs stdin shutdown from Astro configureServer", async () => {
    const integration = litestarAstro()
    const updateConfig = vi.fn()

    await integration.hooks["astro:config:setup"]?.({
      config: {},
      command: "dev",
      isRestart: false,
      updateConfig,
      logger: {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
        label: "test",
      },
    })

    const vitePlugins = updateConfig.mock.calls[0]?.[0]?.vite?.plugins as Array<{ name?: string; configureServer?: (server: TestServer) => void }> | undefined
    const proxyPlugin = vitePlugins?.find((plugin) => plugin.name === "litestar-astro-proxy")
    expect(proxyPlugin).toBeDefined()

    proxyPlugin?.configureServer?.(createServer())

    expectManagedShutdownInstalled()
  })

  it("installs stdin shutdown from Nuxt configureServer", () => {
    const nuxt = { options: { vite: {}, runtimeConfig: {}, nitro: {} } }
    litestarNuxtModule({}, nuxt as never)
    const vitePlugins = (nuxt.options.vite as { plugins?: Array<{ configureServer?: (server: TestServer) => void }> }).plugins
    const proxyPlugin = vitePlugins?.find((plugin) => plugin.configureServer !== undefined)
    expect(proxyPlugin).toBeDefined()

    proxyPlugin?.configureServer?.(createServer())

    expectManagedShutdownInstalled()
  })

  it("installs stdin shutdown from SvelteKit configureServer", () => {
    const plugin = litestarSvelteKit()[0]
    expect(plugin?.configureServer).toBeDefined()

    if (typeof plugin?.configureServer === "function") {
      plugin.configureServer(createServer() as never)
    }

    expectManagedShutdownInstalled()
  })
})
