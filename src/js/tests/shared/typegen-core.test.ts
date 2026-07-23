import type * as FsModule from "node:fs"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  execFile: vi.fn(),
  existsSync: vi.fn(() => true),
  readFileSync: vi.fn(() => JSON.stringify({ bin: { "openapi-ts": "bin/openapi-ts.js" } })),
  resolvePackageExecutorArgv: vi.fn((args: string[], _executor?: string, options?: { packageSpec?: string; additionalPackageSpecs?: readonly string[]; binName?: string }) =>
    options?.packageSpec && options.binName
      ? [
          "npm",
          "exec",
          "--yes",
          "--package",
          options.packageSpec,
          ...(options.additionalPackageSpecs ?? []).flatMap((packageSpec) => ["--package", packageSpec]),
          "--",
          options.binName,
          ...args,
        ]
      : ["npx", ...args],
  ),
  resolve: vi.fn((specifier: string) => {
    if (specifier === "@hey-api/openapi-ts/package.json") {
      return "/fake/node_modules/@hey-api/openapi-ts/package.json"
    }
    return `/fake/node_modules/${specifier}/package.json`
  }),
}))

vi.mock("node:child_process", () => ({
  default: { execFile: mocks.execFile },
  execFile: mocks.execFile,
}))

vi.mock("node:fs", async () => {
  const actual = await vi.importActual<typeof FsModule>("node:fs")
  return {
    ...actual,
    default: {
      ...actual.default,
      existsSync: mocks.existsSync,
      readFileSync: mocks.readFileSync,
    },
    existsSync: mocks.existsSync,
    readFileSync: mocks.readFileSync,
  }
})

vi.mock("node:module", () => ({
  default: { createRequire: vi.fn(() => ({ resolve: mocks.resolve })) },
  createRequire: vi.fn(() => ({ resolve: mocks.resolve })),
}))

vi.mock("../../src/install-hint.js", () => ({
  resolveInstallHint: vi.fn((pkg?: string | readonly string[]) => `npm install -D ${Array.isArray(pkg) ? pkg.join(" ") : pkg || "@hey-api/openapi-ts"}`),
  resolvePackageExecutor: vi.fn((cmd: string) => `npx ${cmd}`),
  resolvePackageExecutorArgv: mocks.resolvePackageExecutorArgv,
}))

vi.mock("../../src/shared/emit-page-props-types.js", () => ({
  emitPagePropsTypes: vi.fn(() => Promise.resolve(false)),
}))

vi.mock("../../src/shared/emit-schemas-types.js", () => ({
  emitSchemasTypes: vi.fn(() => Promise.resolve(false)),
}))

vi.mock("../../src/shared/emit-static-props-types.js", () => ({
  emitStaticPropsTypes: vi.fn(() => Promise.resolve(false)),
}))

import { execFile } from "node:child_process"

import type { TypeGenCoreConfig, TypeGenLogger } from "../../src/shared/typegen-core"
import { findOpenApiTsConfig, resolveDefaultSdkClientPlugin, resolveHeyApiBin, runHeyApiGeneration, runTypeGeneration } from "../../src/shared/typegen-core"

function mockExecFileSuccess(): void {
  mocks.execFile.mockImplementation((...args: unknown[]) => {
    const callback = args.findLast((arg) => typeof arg === "function") as ((error: Error | null, stdout: string, stderr: string) => void) | undefined
    callback?.(null, "", "")
    return {} as ReturnType<typeof execFile>
  })
}

function mockExecFileFailure(error: Error): void {
  mocks.execFile.mockImplementation((...args: unknown[]) => {
    const callback = args.findLast((arg) => typeof arg === "function") as ((error: Error | null, stdout: string, stderr: string) => void) | undefined
    callback?.(error, "", "")
    return {} as ReturnType<typeof execFile>
  })
}

function createConfig(overrides: Partial<TypeGenCoreConfig> = {}): TypeGenCoreConfig {
  return {
    projectRoot: "/home/user/project",
    openapiPath: "openapi.json",
    output: "src/generated",
    pagePropsPath: "inertia-pages.json",
    routesPath: "routes.json",
    generateSdk: true,
    generateZod: false,
    generatePageProps: false,
    generateSchemas: false,
    sdkClientPlugin: "@hey-api/client-fetch",
    ...overrides,
  }
}

describe("resolveDefaultSdkClientPlugin", () => {
  it("uses fetch for all modes", () => {
    expect(resolveDefaultSdkClientPlugin({ mode: "hybrid" })).toBe("@hey-api/client-fetch")
    expect(resolveDefaultSdkClientPlugin({ mode: "spa" })).toBe("@hey-api/client-fetch")
    expect(resolveDefaultSdkClientPlugin({ inertiaMode: true })).toBe("@hey-api/client-fetch")
  })
})

describe("typegen-core", () => {
  let logger: TypeGenLogger

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.existsSync.mockReturnValue(true)
    mocks.readFileSync.mockReturnValue(JSON.stringify({ bin: { "openapi-ts": "bin/openapi-ts.js" } }))
    mocks.resolve.mockImplementation((specifier: string) => {
      if (specifier === "@hey-api/openapi-ts/package.json") {
        return "/fake/node_modules/@hey-api/openapi-ts/package.json"
      }
      return `/fake/node_modules/${specifier}/package.json`
    })
    mockExecFileSuccess()
    logger = {
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }
  })

  it("resolves the locally installed hey-api binary from package.json", () => {
    expect(resolveHeyApiBin("/home/user/project")).toEqual({
      binPath: "/fake/node_modules/@hey-api/openapi-ts/bin/openapi-ts.js",
    })
  })

  it("runs local hey-api through execFile without a shell string", async () => {
    const config = createConfig()

    await runHeyApiGeneration(config, null, ["@hey-api/typescript"], logger)

    expect(execFile).toHaveBeenCalledWith(
      process.execPath,
      ["/fake/node_modules/@hey-api/openapi-ts/bin/openapi-ts.js", "-i", "openapi.json", "-o", "src/generated/api", "--plugins", "@hey-api/typescript"],
      {
        cwd: "/home/user/project",
      },
      expect.any(Function),
    )
  })

  it("runs fallback hey-api through npm exec with an explicit package and binary", async () => {
    mocks.resolve.mockImplementation((specifier: string) => {
      if (specifier === "@hey-api/openapi-ts/package.json") {
        throw new Error("Cannot find module")
      }
      return `/fake/node_modules/${specifier}/package.json`
    })

    await runHeyApiGeneration(createConfig(), null, ["@hey-api/typescript"], logger)

    expect(mocks.resolvePackageExecutorArgv).toHaveBeenCalledWith(["-i", "openapi.json", "-o", "src/generated/api", "--plugins", "@hey-api/typescript"], undefined, {
      packageSpec: "@hey-api/openapi-ts@0.98.2",
      additionalPackageSpecs: ["typescript@6.0.3"],
      binName: "openapi-ts",
    })
    expect(execFile).toHaveBeenCalledWith(
      "npm",
      [
        "exec",
        "--yes",
        "--package",
        "@hey-api/openapi-ts@0.98.2",
        "--package",
        "typescript@6.0.3",
        "--",
        "openapi-ts",
        "-i",
        "openapi.json",
        "-o",
        "src/generated/api",
        "--plugins",
        "@hey-api/typescript",
      ],
      {
        cwd: "/home/user/project",
      },
      expect.any(Function),
    )
  })

  it("classifies missing hey-api as a blocking error", async () => {
    mocks.resolve.mockImplementation(() => {
      throw new Error("Cannot find module")
    })
    mockExecFileFailure(new Error("@hey-api/openapi-ts not installed"))

    const result = await runTypeGeneration(createConfig(), { logger })

    expect(result.errors).toHaveLength(1)
    expect(result.errors[0]).toContain("@hey-api/openapi-ts not installed")
    expect(result.warnings).toEqual([])
    expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("@hey-api/openapi-ts not installed"))
  })

  it("includes zod in the install hint when zod generation is enabled", async () => {
    mocks.resolve.mockImplementation(() => {
      throw new Error("Cannot find module")
    })
    mockExecFileFailure(new Error("@hey-api/openapi-ts not installed"))

    const result = await runTypeGeneration(createConfig({ generateZod: true }), { logger })

    expect(result.errors[0]).toContain("@hey-api/openapi-ts@0.98.2 typescript@6.0.3 zod")
  })

  it("skips SDK generation when openapi.json does not exist", async () => {
    mocks.existsSync.mockImplementation((filePath: string) => !filePath.endsWith("openapi.json"))

    const result = await runTypeGeneration(createConfig(), { logger })

    expect(execFile).not.toHaveBeenCalled()
    expect(result.generated).toBe(false)
  })

  it("detects hey-api config with JavaScript module extensions", () => {
    mocks.existsSync.mockImplementation((filePath: string) => filePath.endsWith("openapi-ts.config.mjs"))

    expect(findOpenApiTsConfig("/home/user/project")).toBe("/home/user/project/openapi-ts.config.mjs")
  })

  it("prefers TypeScript hey-api config over JavaScript variants", () => {
    mocks.existsSync.mockImplementation((filePath: string) => filePath.endsWith("openapi-ts.config.ts") || filePath.endsWith("openapi-ts.config.mjs"))

    expect(findOpenApiTsConfig("/home/user/project")).toBe("/home/user/project/openapi-ts.config.ts")
  })
})
