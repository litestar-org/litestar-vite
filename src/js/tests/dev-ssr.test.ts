// @vitest-environment node
import fsSync from "node:fs"
import fs from "node:fs/promises"
import http from "node:http"
import os from "node:os"
import path from "node:path"
import { createServer, type ViteDevServer } from "vite"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { litestarViteSsrPlugin } from "../src/dev-ssr.js"
import type { DevSsrOptions } from "../src/shared/ssr-types.js"

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
}

describe("backend-only development SSR", () => {
  let directory: string
  let server: ViteDevServer | undefined
  let baseUrl: string
  let originalConfigPath: string | undefined

  beforeEach(async () => {
    originalConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
    directory = await fs.mkdtemp(path.join(os.tmpdir(), "litestar-dev-ssr-"))
    process.env.LITESTAR_VITE_CONFIG_PATH = path.join(directory, "missing.litestar.json")
    await fs.mkdir(path.join(directory, "app/components"), { recursive: true })
    await fs.writeFile(path.join(directory, "app/ssr.js"), "export default (page) => ({ head: [], body: page.message })")
    await fs.writeFile(path.join(directory, "app/components/Counter.tsx"), "export default () => null")
    await fs.writeFile(path.join(directory, "outside.tsx"), "export default () => null")
  })

  afterEach(async () => {
    vi.restoreAllMocks()
    await server?.close()
    server = undefined
    if (originalConfigPath === undefined) {
      delete process.env.LITESTAR_VITE_CONFIG_PATH
    } else {
      process.env.LITESTAR_VITE_CONFIG_PATH = originalConfigPath
    }
    await fs.rm(directory, { recursive: true, force: true })
  })

  async function start(options: DevSsrOptions = { entrypoint: "ssr.js", componentRoots: ["components"] }) {
    server = await createServer({
      configFile: false,
      root: path.join(directory, "app"),
      logLevel: "silent",
      plugins: [litestarViteSsrPlugin(options)],
      server: { host: "127.0.0.1", port: 0, fs: { strict: true, allow: [path.join(directory, "app")] } },
    })
    await server.listen()
    const address = server.httpServer!.address()
    if (!address || typeof address === "string") throw new Error("Expected TCP listener")
    baseUrl = `http://127.0.0.1:${address.port}`
  }

  function post(payload: unknown, headers: Record<string, string> = { "Content-Type": "application/json" }, endpoint = "") {
    return fetch(`${baseUrl}/__litestar_ssr__${endpoint}`, { method: "POST", headers, body: JSON.stringify(payload) })
  }

  function postRawWithoutContentType(endpoint = "", headers: Record<string, string> = {}): Promise<number> {
    return new Promise((resolve, reject) => {
      const target = new URL(`${baseUrl}/__litestar_ssr__${endpoint}`)
      const req = http.request(
        {
          hostname: target.hostname,
          port: target.port,
          path: target.pathname,
          method: "POST",
          headers,
        },
        (res) => {
          res.resume()
          resolve(res.statusCode ?? 0)
        },
      )
      req.on("error", reject)
      req.end(JSON.stringify({}))
    })
  }

  it("renders the configured entrypoint for Python-style IPC requests", async () => {
    await start()
    const response = await post({ id: 1, method: "render", params: { message: "Hello" } })
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ id: 1, result: { head: [], body: "Hello" } })
  })

  it("does not mount the endpoint without configured SSR or fragments", async () => {
    await start({})
    expect((await post({})).status).toBe(404)
  })

  it("rejects request-selected entrypoints even within the application", async () => {
    await start()
    const response = await post({ entrypoint: "ssr.js", params: {} })
    expect(response.status).toBe(500)
    const body = await response.json()
    expect(body.error.message).toContain("entrypoints must be configured")
    expect(body.error.stack).toBeUndefined()
  })

  it.each(["https://untrusted.example", "null", "http://localhost:5173"])("rejects browser origin %s", async (origin) => {
    await start()
    expect((await post({}, { "Content-Type": "application/json", Origin: origin })).status).toBe(403)
    expect((await post({}, { "Content-Type": "application/json", Origin: origin }, "/invalidate")).status).toBe(403)
  })

  it("rejects browser fetch metadata and simple form content types", async () => {
    await start()
    expect((await post({}, { "Content-Type": "application/json", "Sec-Fetch-Site": "same-origin" })).status).toBe(403)
    expect((await post({}, { "Content-Type": "text/plain" })).status).toBe(415)
  })

  it("rejects POST requests missing Content-Type header with 415", async () => {
    await start({ entrypoint: "ssr.js", proxyToken: "secret-tok" })
    expect(await postRawWithoutContentType("", { "X-Litestar-Proxy-Token": "secret-tok" })).toBe(415)
    expect(await postRawWithoutContentType("/invalidate", { "X-Litestar-Proxy-Token": "secret-tok" })).toBe(415)
  })

  it("enforces configured proxyToken on render and /invalidate", async () => {
    await start({ entrypoint: "ssr.js", proxyToken: "secret-tok" })

    expect((await post({ id: 1, params: { message: "nope" } })).status).toBe(403)
    expect((await post({}, { "Content-Type": "application/json" }, "/invalidate")).status).toBe(403)
    expect((await post({ id: 1, params: { message: "nope" } }, { "Content-Type": "application/json", "X-Litestar-Proxy-Token": "wrong-tok" })).status).toBe(403)
    expect((await post({}, { "Content-Type": "application/json", "X-Litestar-Proxy-Token": "wrong-tok" }, "/invalidate")).status).toBe(403)

    const validRender = await post({ id: 2, params: { message: "ok" } }, { "Content-Type": "application/json", "X-Litestar-Proxy-Token": "secret-tok" })
    expect(validRender.status).toBe(200)
    expect(await validRender.json()).toEqual({ id: 2, result: { head: [], body: "ok" } })

    const validInvalidate = await post({}, { "Content-Type": "application/json", "X-Litestar-Proxy-Token": "secret-tok" }, "/invalidate")
    expect(validInvalidate.status).toBe(200)
    expect(await validInvalidate.json()).toEqual({ success: true, message: "SSR cache cleared" })
  })

  it("reads proxyToken from .litestar.json via LITESTAR_VITE_CONFIG_PATH", async () => {
    const bridgePath = path.join(directory, ".litestar.json")
    await fs.writeFile(bridgePath, JSON.stringify({ ...baseBridgeConfig, proxyToken: "bridge-tok" }))
    process.env.LITESTAR_VITE_CONFIG_PATH = bridgePath

    await start({ entrypoint: "ssr.js" })

    expect((await post({ id: 1, params: { message: "nope" } })).status).toBe(403)
    expect((await post({}, { "Content-Type": "application/json" }, "/invalidate")).status).toBe(403)

    const okRender = await post({ id: 3, params: { message: "from-bridge" } }, { "Content-Type": "application/json", "X-Litestar-Proxy-Token": "bridge-tok" })
    expect(okRender.status).toBe(200)
    expect(await okRender.json()).toEqual({ id: 3, result: { head: [], body: "from-bridge" } })
  })

  it("renders a component within the configured roots", async () => {
    await start()
    const response = await post({ method: "render_fragment", params: { component: "components/Counter.tsx" } })
    expect(response.status).toBe(200)
    expect((await response.json()).result.html).toBe("")
  })

  it("rejects traversal, absolute paths outside roots, and symlinks outside roots before realpathSync", async () => {
    await fs.symlink(path.join(directory, "outside.tsx"), path.join(directory, "app/components/Escape.tsx"))
    await start()
    const realpathSpy = vi.spyOn(fsSync, "realpathSync")
    const outsideAbsolute = path.join(directory, "outside.tsx")

    for (const component of ["../outside.tsx", outsideAbsolute, "components/Escape.tsx", "/@fs/anything.tsx"]) {
      const response = await post({ method: "render_fragment", params: { component } })
      expect(response.status).toBe(500)
      const body = await response.json()
      expect(body.error.message).toMatch(/outside the configured|Invalid fragment/)
      expect(body.error.stack).toBeUndefined()
    }

    const calledWithOutside = realpathSpy.mock.calls.some(([target]) => String(target).endsWith("outside.tsx"))
    expect(calledWithOutside).toBe(false)
  })

  it("logs missing fragment resolution errors locally without returning lstat or stack over HTTP", async () => {
    await start()
    const loggerErrorSpy = vi.spyOn(server!.config.logger, "error")

    const response = await post({ id: 9, method: "render_fragment", params: { component: "components/DoesNotExist.tsx" } })
    expect(response.status).toBe(500)
    const rawBody = await response.text()
    expect(rawBody).not.toContain("lstat")
    expect(rawBody).not.toContain(directory)

    const body = JSON.parse(rawBody)
    expect(body.id).toBe(9)
    expect(body.error.message).toBe("Fragment component could not be resolved.")
    expect(body.error.stack).toBeUndefined()
    expect(loggerErrorSpy).toHaveBeenCalled()
    expect(loggerErrorSpy.mock.calls.map((call) => String(call[0])).join("\n")).toContain("DoesNotExist.tsx")
  })

  it("logs runtime render exceptions locally without returning internal details or stack over HTTP", async () => {
    await fs.writeFile(path.join(directory, "app/ssr.js"), 'export default () => { throw new Error("secret internal /abs/path detail") }')
    await start({ entrypoint: "ssr.js" })
    const loggerErrorSpy = vi.spyOn(server!.config.logger, "error")

    const response = await post({ id: 10, method: "render", params: {} })
    expect(response.status).toBe(500)
    const rawBody = await response.text()
    expect(rawBody).not.toContain("secret internal")
    expect(rawBody).not.toContain("/abs/path")
    expect(rawBody).not.toContain(directory)

    const body = JSON.parse(rawBody)
    expect(body).toEqual({
      id: 10,
      error: {
        message: "SSR render error",
      },
    })
    expect(loggerErrorSpy).toHaveBeenCalled()
    expect(loggerErrorSpy.mock.calls.map((call) => String(call[0])).join("\n")).toContain("secret internal /abs/path detail")
  })

  it("does not enable fragment imports when only SSR is configured", async () => {
    await start({ entrypoint: "ssr.js" })
    const response = await post({ method: "render_fragment", params: { component: "components/Counter.tsx" } })
    expect(response.status).toBe(500)
    const body = await response.json()
    expect(body.error.message).toContain("outside the configured")
    expect(body.error.stack).toBeUndefined()
  })
})
