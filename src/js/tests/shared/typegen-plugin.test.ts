import type * as FsModule from "node:fs"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  existsSync: vi.fn(() => true),
  runTypeGeneration: vi.fn(),
  stat: vi.fn(() => Promise.resolve({ mtimeMs: 1 })),
}))

vi.mock("node:fs", async () => {
  const actual = await vi.importActual<typeof FsModule>("node:fs")
  return {
    ...actual,
    default: {
      ...actual.default,
      existsSync: mocks.existsSync,
      promises: {
        ...actual.promises,
        stat: mocks.stat,
      },
    },
    existsSync: mocks.existsSync,
    promises: {
      ...actual.promises,
      stat: mocks.stat,
    },
  }
})

vi.mock("../../src/shared/typegen-core.js", () => ({
  runTypeGeneration: mocks.runTypeGeneration,
}))

import { createLitestarTypeGenPlugin, type RequiredTypeGenConfig } from "../../src/shared/typegen-plugin"

const baseConfig: RequiredTypeGenConfig = {
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
  debounce: 1,
}

function result(overrides: Partial<Awaited<ReturnType<typeof mocks.runTypeGeneration>>> = {}) {
  return {
    generated: false,
    generatedFiles: [],
    skippedFiles: [],
    durationMs: 1,
    warnings: [],
    errors: [],
    ...overrides,
  }
}

function createPlugin(config: Partial<RequiredTypeGenConfig> = {}) {
  return createLitestarTypeGenPlugin(
    { ...baseConfig, ...config },
    {
      pluginName: "litestar-test-types",
      frameworkName: "litestar-test",
      sdkClientPlugin: "@hey-api/client-fetch",
      hasPythonConfig: true,
    },
  )
}

function createResolvedConfig(command: "build" | "serve") {
  return {
    command,
    root: "/project",
    logger: {
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    },
  }
}

describe("createLitestarTypeGenPlugin", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.existsSync.mockReturnValue(true)
    mocks.stat.mockResolvedValue({ mtimeMs: 1 })
    mocks.runTypeGeneration.mockResolvedValue(result())
  })

  it("fails vite build on typegen errors by default", async () => {
    mocks.runTypeGeneration.mockResolvedValue(result({ errors: ["hey-api failed"] }))
    const plugin = createPlugin()
    plugin.configResolved?.(createResolvedConfig("build") as never)
    const context = { error: vi.fn(), warn: vi.fn() }

    await plugin.buildStart?.call(context as never)

    expect(context.error).toHaveBeenCalledWith(expect.stringContaining("hey-api failed"))
    expect(context.warn).not.toHaveBeenCalled()
  })

  it("warns during serve when failOnError is omitted", async () => {
    mocks.runTypeGeneration.mockResolvedValue(result({ errors: ["hey-api failed"] }))
    const plugin = createPlugin()
    plugin.configResolved?.(createResolvedConfig("serve") as never)
    const context = { error: vi.fn(), warn: vi.fn() }

    await plugin.buildStart?.call(context as never)

    expect(context.warn).toHaveBeenCalledWith(expect.stringContaining("hey-api failed"))
    expect(context.error).not.toHaveBeenCalled()
  })

  it("honors failOnError false during build", async () => {
    mocks.runTypeGeneration.mockResolvedValue(result({ errors: ["hey-api failed"] }))
    const plugin = createPlugin({ failOnError: false })
    plugin.configResolved?.(createResolvedConfig("build") as never)
    const context = { error: vi.fn(), warn: vi.fn() }

    await plugin.buildStart?.call(context as never)

    expect(context.warn).toHaveBeenCalledWith(expect.stringContaining("hey-api failed"))
    expect(context.error).not.toHaveBeenCalled()
  })

  it("reruns once when a change arrives during active generation", async () => {
    let resolveFirst: (value: unknown) => void = () => undefined
    const firstRun = new Promise((resolve) => {
      resolveFirst = resolve
    })
    mocks.runTypeGeneration.mockReturnValueOnce(firstRun).mockResolvedValueOnce(result())

    const plugin = createPlugin()
    plugin.configResolved?.(createResolvedConfig("build") as never)
    const context = { error: vi.fn(), warn: vi.fn() }

    const first = plugin.buildStart?.call(context as never)
    const second = plugin.buildStart?.call(context as never)
    expect(mocks.runTypeGeneration).toHaveBeenCalledTimes(1)

    resolveFirst(result())
    await Promise.all([first, second])

    expect(mocks.runTypeGeneration).toHaveBeenCalledTimes(2)
  })

  it("regenerates after routes.json changes", async () => {
    vi.useFakeTimers()
    mocks.runTypeGeneration.mockResolvedValue(result({ generated: true, generatedFiles: ["src/generated/schemas.ts"] }))
    const plugin = createPlugin()
    plugin.configResolved?.(createResolvedConfig("serve") as never)

    await plugin.handleHotUpdate?.({ file: "/project/src/generated/routes.json" } as never)
    await vi.runAllTimersAsync()

    expect(mocks.runTypeGeneration).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})
