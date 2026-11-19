import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { describe, expect, it, vi } from "vitest"
import {
  BRIDGE_PROXY_TOKEN_HEADER,
  isJsonContentType,
  isLoopbackAddress,
  parseBridgeSchema,
  readBridgeConfig,
  timingSafeTokenEqual,
  verifyBridgeRequest,
} from "../../src/shared/bridge-schema"

const baseBridgeConfig = {
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
} as const

describe("bridge schema appUrl", () => {
  it("accepts a string appUrl", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      appUrl: "http://127.0.0.1:8000",
    })

    expect(config.appUrl).toBe("http://127.0.0.1:8000")
  })

  it("accepts a null appUrl", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      appUrl: null,
    })

    expect(config.appUrl).toBeNull()
  })

  it("treats a missing appUrl as null for older bridge files", () => {
    const config = parseBridgeSchema(baseBridgeConfig)

    expect(config.appUrl).toBeNull()
  })
})

describe("bridge schema mode contract", () => {
  it("rejects alias modes because Python writes canonical modes", () => {
    for (const mode of ["htmx", "inertia", "ssr", "ssg"]) {
      expect(() => parseBridgeSchema({ ...baseBridgeConfig, mode })).toThrow(`"mode" must be one of`)
    }
  })
})

describe("bridge schema litestarPort", () => {
  it("accepts a numeric litestarPort", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, litestarPort: 8000 })
    expect(config.litestarPort).toBe(8000)
  })

  it("accepts a null litestarPort", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, litestarPort: null })
    expect(config.litestarPort).toBeNull()
  })

  it("treats a missing litestarPort as null for older bridge files", () => {
    const config = parseBridgeSchema(baseBridgeConfig)
    expect(config.litestarPort).toBeNull()
  })

  it("rejects non-integer litestarPort", () => {
    expect(() => parseBridgeSchema({ ...baseBridgeConfig, litestarPort: "8000" })).toThrow(/litestarPort/)
  })
})

describe("bridge schema csrf names", () => {
  it("accepts string csrfCookieName/csrfHeaderName", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      csrfCookieName: "custom_cookie",
      csrfHeaderName: "x-custom-header",
    })
    expect(config.csrfCookieName).toBe("custom_cookie")
    expect(config.csrfHeaderName).toBe("x-custom-header")
  })

  it("accepts null csrfCookieName/csrfHeaderName", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      csrfCookieName: null,
      csrfHeaderName: null,
    })
    expect(config.csrfCookieName).toBeNull()
    expect(config.csrfHeaderName).toBeNull()
  })

  it("treats missing csrfCookieName/csrfHeaderName as null for older bridge files", () => {
    const config = parseBridgeSchema(baseBridgeConfig)
    expect(config.csrfCookieName).toBeNull()
    expect(config.csrfHeaderName).toBeNull()
  })
})

describe("bridge schema additive fields", () => {
  it("warns and ignores unknown top-level keys", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, futureField: true })

    expect(config.assetUrl).toBe("/static")
    expect("futureField" in config).toBe(false)
  })

  it("returns null for corrupt bridge JSON", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-bridge-"))
    const configPath = path.join(tmpDir, ".litestar.json")
    fs.writeFileSync(configPath, "{")

    try {
      expect(readBridgeConfig(configPath)).toBeNull()
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })

  it("memoizes bridge file reads until path mtime changes", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-bridge-"))
    const configPath = path.join(tmpDir, ".litestar.json")
    fs.writeFileSync(configPath, JSON.stringify(baseBridgeConfig))
    const readSpy = vi.spyOn(fs, "readFileSync")

    try {
      expect(readBridgeConfig(configPath)?.port).toBe(5173)
      expect(readBridgeConfig(configPath)?.port).toBe(5173)
      expect(readSpy).toHaveBeenCalledTimes(1)

      fs.writeFileSync(configPath, JSON.stringify({ ...baseBridgeConfig, port: 5174 }))
      const mtime = new Date(Date.now() + 1000)
      fs.utimesSync(configPath, mtime, mtime)

      expect(readBridgeConfig(configPath)?.port).toBe(5174)
      expect(readSpy).toHaveBeenCalledTimes(2)
    } finally {
      readSpy.mockRestore()
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })
})

describe("bridge schema typegen failOnError", () => {
  const types = {
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
  }

  it("parses an explicit failOnError value", () => {
    const config = parseBridgeSchema({ ...baseBridgeConfig, types: { ...types, failOnError: false } })

    expect(config.types?.failOnError).toBe(false)
  })

  it("preserves failOnError as undefined when the bridge omits it or writes null", () => {
    const omitted = parseBridgeSchema({ ...baseBridgeConfig, types })
    const nullValue = parseBridgeSchema({ ...baseBridgeConfig, types: { ...types, failOnError: null } })

    expect(omitted.types?.failOnError).toBeUndefined()
    expect(nullValue.types?.failOnError).toBeUndefined()
  })
})

describe("bridge schema null routesTsPath and schemasTsPath", () => {
  it("accepts null routesTsPath and schemasTsPath from Python config", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      types: {
        enabled: true,
        output: "src/generated",
        openapiPath: "openapi.json",
        routesPath: "routes.json",
        pagePropsPath: "inertia-pages.json",
        routesTsPath: null,
        schemasTsPath: null,
        generateZod: false,
        generateSdk: true,
        generateRoutes: true,
        generatePageProps: true,
        generateSchemas: true,
        globalRoute: false,
      },
    })

    expect(config.types?.routesTsPath).toBeNull()
    expect(config.types?.schemasTsPath).toBeNull()
  })

  it("accepts asyncapiPath, channelsTsPath, and generateChannels from Python config", () => {
    const config = parseBridgeSchema({
      ...baseBridgeConfig,
      types: {
        enabled: true,
        output: "src/generated",
        openapiPath: "src/generated/openapi.json",
        routesPath: "src/generated/routes.json",
        pagePropsPath: "src/generated/inertia-pages.json",
        asyncapiPath: "src/generated/asyncapi.json",
        channelsTsPath: "src/generated/channels.ts",
        generateZod: false,
        generateSdk: true,
        generateRoutes: true,
        generatePageProps: true,
        generateChannels: true,
        generateSchemas: true,
        globalRoute: false,
      },
    })

    expect(config.types?.asyncapiPath).toBe("src/generated/asyncapi.json")
    expect(config.types?.channelsTsPath).toBe("src/generated/channels.ts")
    expect(config.types?.generateChannels).toBe(true)
  })
})

describe("bridge schema proxyToken", () => {
  it("parses string, null, and omitted proxyToken without unknown-key warnings", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
    try {
      const withToken = parseBridgeSchema({ ...baseBridgeConfig, proxyToken: "test-token-placeholder" })
      const withNull = parseBridgeSchema({ ...baseBridgeConfig, proxyToken: null })
      const omitted = parseBridgeSchema(baseBridgeConfig)

      expect(withToken.proxyToken).toBe("test-token-placeholder")
      expect(withNull.proxyToken).toBeNull()
      expect(omitted.proxyToken).toBeNull()
      expect(warnSpy).not.toHaveBeenCalled()
    } finally {
      warnSpy.mockRestore()
    }
  })

  it.each([123, true, { value: "bad" }])("rejects non-string proxyToken value %j", (invalidToken) => {
    expect(() => parseBridgeSchema({ ...baseBridgeConfig, proxyToken: invalidToken })).toThrow(/"proxyToken" must be a string or null/)
  })
})

describe("bridge request verification helpers", () => {
  it("exports the canonical proxy token header name", () => {
    expect(BRIDGE_PROXY_TOKEN_HEADER).toBe("x-litestar-proxy-token")
  })

  it.each([
    ["exact match", "test-token-placeholder", "test-token-placeholder", true],
    ["same-length mismatch", "test-token-placeholdeX", "test-token-placeholder", false],
    ["shorter mismatch", "short", "test-token-placeholder", false],
    ["longer mismatch", "test-token-placeholder-extra", "test-token-placeholder", false],
    ["undefined header", undefined, "test-token-placeholder", false],
    ["duplicate header array", ["test-token-placeholder"], "test-token-placeholder", false],
    ["multi-value header array", ["test-token-placeholder", "other"], "test-token-placeholder", false],
    ["empty expected token", "", "", false],
  ] as const)("timingSafeTokenEqual handles %s", (_label, provided, expected, outcome) => {
    expect(timingSafeTokenEqual(provided as string | string[] | undefined, expected)).toBe(outcome)
  })

  it.each([
    ["127.0.0.1", true],
    ["127.0.0.2", true],
    ["127.255.255.254", true],
    ["::1", true],
    ["::ffff:127.0.0.1", true],
    ["::FFFF:127.1.2.3", true],
    ["192.168.1.5", false],
    ["::ffff:192.168.1.5", false],
    ["0.0.0.0", false],
    ["::", false],
    ["127.0.0.999", false],
    ["127.evil.com", false],
    ["", false],
    [undefined, false],
  ] as const)("isLoopbackAddress(%j) returns %s", (address, expected) => {
    expect(isLoopbackAddress(address)).toBe(expected)
  })

  it.each([
    ["application/json", true],
    ["application/json; charset=utf-8", true],
    ["APPLICATION/JSON;charset=UTF-8", true],
    ["text/plain", false],
    ["application/x-www-form-urlencoded", false],
    [undefined, false],
    [["application/json", "text/plain"], false],
  ] as const)("isJsonContentType(%j) returns %s", (value, expected) => {
    expect(isJsonContentType(value as string | string[] | undefined)).toBe(expected)
  })

  it.each([
    [
      "valid token and JSON content type",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: "test-token-placeholder",
          "content-type": "application/json; charset=utf-8",
        },
        socket: { remoteAddress: "10.0.0.5" },
      },
      "test-token-placeholder",
      { ok: true },
    ],
    [
      "wrong token",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: "wrong-token",
          "content-type": "application/json",
        },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      { ok: false, statusCode: 403, message: "Forbidden" },
    ],
    [
      "missing token header",
      {
        headers: { "content-type": "application/json" },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      { ok: false, statusCode: 403, message: "Forbidden" },
    ],
    [
      "duplicate token header array",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: ["test-token-placeholder", "test-token-placeholder"],
          "content-type": "application/json",
        },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      { ok: false, statusCode: 403, message: "Forbidden" },
    ],
    [
      "standalone loopback IPv4",
      {
        headers: { "content-type": "application/json" },
        socket: { remoteAddress: "127.0.0.1" },
      },
      null,
      { ok: true },
    ],
    [
      "standalone loopback IPv6",
      {
        headers: { "content-type": "application/json" },
        socket: { remoteAddress: "::1" },
      },
      undefined,
      { ok: true },
    ],
    [
      "standalone non-loopback rejected",
      {
        headers: { "content-type": "application/json" },
        socket: { remoteAddress: "192.168.1.5" },
      },
      null,
      { ok: false, statusCode: 403, message: "Forbidden" },
    ],
    [
      "missing content-type returns 415",
      {
        headers: { [BRIDGE_PROXY_TOKEN_HEADER]: "test-token-placeholder" },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      { ok: false, statusCode: 415, message: "Unsupported content type" },
    ],
    [
      "wrong content-type returns 415",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: "test-token-placeholder",
          "content-type": "text/plain",
        },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      { ok: false, statusCode: 415, message: "Unsupported content type" },
    ],
    [
      "Origin header rejected with 403",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: "test-token-placeholder",
          "content-type": "application/json",
          origin: "https://evil.example",
        },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      {
        ok: false,
        statusCode: 403,
        message: "Browser requests are not allowed on internal bridge endpoints",
      },
    ],
    [
      "Sec-Fetch-Site header rejected with 403",
      {
        headers: {
          [BRIDGE_PROXY_TOKEN_HEADER]: "test-token-placeholder",
          "content-type": "application/json",
          "sec-fetch-site": "same-origin",
        },
        socket: { remoteAddress: "127.0.0.1" },
      },
      "test-token-placeholder",
      {
        ok: false,
        statusCode: 403,
        message: "Browser requests are not allowed on internal bridge endpoints",
      },
    ],
  ])("verifyBridgeRequest: %s", (_label, req, expectedToken, expectedResult) => {
    expect(verifyBridgeRequest(req, expectedToken)).toEqual(expectedResult)
  })
})
