import fs from "node:fs"
import os from "node:os"
import path from "node:path"

import { createServer, type ViteDevServer } from "vite"
import { afterEach, describe, expect, it } from "vitest"

import litestar from "../src"

describe("secondary HTML entry transformation", () => {
  let server: ViteDevServer | undefined
  let root: string | undefined

  afterEach(async () => {
    await server?.close()
    if (root) fs.rmSync(root, { recursive: true, force: true })
  })

  it("transforms an exact secondary document from the configured Vite root", async () => {
    root = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-vite-html-entry-"))
    fs.writeFileSync(path.join(root, "offline.html"), '<html><head></head><body><script type="module" src="/offline.ts"></script></body></html>')
    fs.writeFileSync(path.join(root, "offline.ts"), "console.log('offline')")
    server = await createServer({
      configFile: false,
      root,
      logLevel: "silent",
      plugins: litestar({ input: "offline.ts", hotFile: path.join(root, "hot"), autoDetectIndex: false }),
      server: { host: "127.0.0.1", port: 0 },
    })
    await server.listen()
    const address = server.httpServer?.address()
    if (!address || typeof address === "string") throw new Error("Vite did not expose a TCP address")

    const response = await fetch(`http://127.0.0.1:${address.port}/__litestar__/transform-index`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ entry: "offline.html" }),
    })
    const html = await response.text()

    expect(response.status).toBe(200)
    expect(html).toContain("/@vite/client")
    expect(html).toContain('src="/static/offline.ts"')
    expect(html).not.toContain("index.html")
  })
})
