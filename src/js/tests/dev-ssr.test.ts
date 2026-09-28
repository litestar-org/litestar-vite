// @vitest-environment node
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { createServer, type ViteDevServer } from "vite"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { litestarViteSsrPlugin } from "../src/dev-ssr.js"
import type { DevSsrOptions } from "../src/shared/ssr-types.js"

describe("backend-only development SSR", () => {
  let directory: string
  let server: ViteDevServer | undefined
  let baseUrl: string

  beforeEach(async () => {
    directory = await fs.mkdtemp(path.join(os.tmpdir(), "litestar-dev-ssr-"))
    await fs.mkdir(path.join(directory, "app/components"), { recursive: true })
    await fs.writeFile(path.join(directory, "app/ssr.js"), "export default (page) => ({ head: [], body: page.message })")
    await fs.writeFile(path.join(directory, "app/components/Counter.tsx"), "export default () => null")
    await fs.writeFile(path.join(directory, "outside.tsx"), "export default () => null")
  })

  afterEach(async () => {
    await server?.close()
    server = undefined
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
    expect((await response.json()).error.message).toContain("entrypoints must be configured")
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

  it("renders a component within the configured roots", async () => {
    await start()
    const response = await post({ method: "render_fragment", params: { component: "components/Counter.tsx" } })
    expect(response.status).toBe(200)
    expect((await response.json()).result.html).toBe("")
  })

  it("rejects traversal, absolute paths outside roots, and symlinks outside roots", async () => {
    await fs.symlink(path.join(directory, "outside.tsx"), path.join(directory, "app/components/Escape.tsx"))
    await start()
    for (const component of ["../outside.tsx", path.join(directory, "outside.tsx"), "components/Escape.tsx", "/@fs/anything.tsx"]) {
      const response = await post({ method: "render_fragment", params: { component } })
      expect(response.status).toBe(500)
      expect((await response.json()).error.message).toMatch(/outside the configured|Invalid fragment/)
    }
  })

  it("does not enable fragment imports when only SSR is configured", async () => {
    await start({ entrypoint: "ssr.js" })
    const response = await post({ method: "render_fragment", params: { component: "components/Counter.tsx" } })
    expect(response.status).toBe(500)
    expect((await response.json()).error.message).toContain("outside the configured")
  })
})
