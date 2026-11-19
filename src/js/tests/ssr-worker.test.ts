// @vitest-environment node
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { pathToFileURL } from "node:url"
import { afterEach, describe, expect, it, vi } from "vitest"
import { isDirectCliInvocation, resolveSsrWorkerCliOptions } from "../src/ssr-worker-cli.js"
import { dispatchSsrRequest, startSsrWorker } from "../src/ssr-worker.js"

const createdDirs: string[] = []

function makeTempDir(prefix: string): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix))
  createdDirs.push(dir)
  return dir
}

function writeBridgeConfigFile(filePath: string, overrides: Record<string, unknown> = {}): void {
  const payload = {
    assetUrl: "/static/",
    deployAssetUrl: null,
    appUrl: "http://127.0.0.1:8000",
    csrfCookieName: "csrftoken",
    csrfHeaderName: "X-CSRFToken",
    proxyToken: "test-bridge-token-placeholder",
    litestarPort: 8000,
    bundleDir: "public/build",
    resourceDir: "resources",
    staticDir: "public",
    hotFile: "public/hot",
    manifest: "manifest.json",
    mode: "hybrid",
    proxyMode: "vite",
    host: "127.0.0.1",
    port: 5173,
    ssrOutDir: null,
    types: null,
    spa: null,
    executor: "node",
    logging: null,
    litestarVersion: "0.33.1",
    staticProps: null,
    ...overrides,
  }
  fs.writeFileSync(filePath, JSON.stringify(payload), "utf8")
}

describe("SSR worker dispatch", () => {
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__
    vi.restoreAllMocks()
    while (createdDirs.length > 0) {
      const dir = createdDirs.pop()
      if (dir) {
        fs.rmSync(dir, { recursive: true, force: true })
      }
    }
  })

  it("renders application pages and dispatches fragments separately", async () => {
    const options = {
      render: (page: any) => `<main>${page.component}</main>`,
      renderFragment: (params: Record<string, unknown>) => ({ html: `<aside>${params.component}</aside>` }),
    }
    await expect(dispatchSsrRequest({ method: "render", params: { page: { component: "Home" } } }, options)).resolves.toEqual({ head: [], body: "<main>Home</main>" })
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card.tsx" } }, options)).resolves.toEqual({ html: "<aside>Card.tsx</aside>" })
  })

  it("preserves direct Python Inertia page parameters including their props", async () => {
    const page = { component: "Home", props: { message: "SSR body" }, url: "/", version: "1" }
    let received: unknown
    const result = await dispatchSsrRequest(
      { id: 1, method: "render", params: page },
      {
        render: (value) => {
          received = value
          return `<main>${value.component}: ${value.props.message}</main>`
        },
      },
    )
    expect(received).toBe(page)
    expect(result).toEqual({ head: [], body: "<main>Home: SSR body</main>" })
  })

  it("propagates failures instead of returning placeholder HTML", async () => {
    const ssrDir = makeTempDir("litestar-ssr-missing-")
    await expect(dispatchSsrRequest({ method: "render" })).rejects.toThrow("SSR requires")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "missing-render-module.mjs" } })).rejects.toThrow("requires a configured ssrDir")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "missing-render-module.mjs" } }, { ssrDir })).rejects.toThrow("SSR entrypoint could not be resolved")
    await expect(
      dispatchSsrRequest(
        { method: "render" },
        {
          render: () => {
            throw new Error("render failed")
          },
        },
      ),
    ).rejects.toThrow("render failed")
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card.tsx" } })).rejects.toThrow("compiled component registry")
    await expect(dispatchSsrRequest({ method: "unknown" })).rejects.toThrow("Unsupported method")
  })

  it("registers globalThis.__litestar_ssr_dispatch__ for WebWorker and WASM runtimes", async () => {
    const stdinOnSpy = vi.spyOn(process.stdin, "on").mockImplementation(() => process.stdin)
    startSsrWorker({
      render: (page: any) => `<section>${page.component}</section>`,
      renderFragment: (params: Record<string, unknown>) => ({ html: `<div>${params.component}</div>` }),
    })

    expect(stdinOnSpy).toHaveBeenCalledWith("data", expect.any(Function))
    const dispatch = (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__ as ((line: string) => Promise<string>) | undefined
    expect(typeof dispatch).toBe("function")

    const emptyOut = await dispatch!("   ")
    expect(emptyOut).toBe("")

    const pingOut = JSON.parse(await dispatch!(JSON.stringify({ id: "p1", method: "ping" })))
    expect(pingOut).toEqual({ id: "p1", result: { status: "pong" } })

    const fragOut = JSON.parse(await dispatch!(JSON.stringify({ id: 2, method: "render_fragment", params: { component: "Hero" } })))
    expect(fragOut).toEqual({ id: 2, result: { html: "<div>Hero</div>" } })

    const renderOut = JSON.parse(await dispatch!(JSON.stringify({ id: 3, method: "render", params: { page: { component: "Dashboard" } } })))
    expect(renderOut).toEqual({ id: 3, result: { head: [], body: "<section>Dashboard</section>" } })

    const errOut = JSON.parse(await dispatch!(JSON.stringify({ id: 4, method: "unknown_op" })))
    expect(errOut.id).toBe(4)
    expect(errOut.error).toContain("Unsupported method: unknown_op")
  })

  it("buffers chunked and multi-line process.stdin data without node:readline", async () => {
    let dataHandler: ((chunk: string | Uint8Array) => void) | undefined
    vi.spyOn(process.stdin, "on").mockImplementation(((event: string, listener: (chunk: string | Uint8Array) => void) => {
      if (event === "data") {
        dataHandler = listener
      }
      return process.stdin
    }) as any)
    const writes: string[] = []
    vi.spyOn(process.stdout, "write").mockImplementation(((chunk: string | Uint8Array) => {
      writes.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk))
      return true
    }) as any)

    startSsrWorker({
      render: (page: any) => `<h1>${page.component}</h1>`,
    })

    expect(dataHandler).toBeDefined()
    dataHandler!('{"id":10,"method":')
    expect(writes).toHaveLength(0)

    dataHandler!('"ping"}\n{"id":11,"method":"render","params":{"page":{"component":"Settings"}}}\n')
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(writes).toHaveLength(2)
    expect(JSON.parse(writes[0])).toEqual({ id: 10, result: { status: "pong" } })
    expect(JSON.parse(writes[1])).toEqual({ id: 11, result: { head: [], body: "<h1>Settings</h1>" } })
  })

  it("decodes multibyte UTF-8 split across binary chunks and exits on stdin EOF after draining", async () => {
    const listeners: Record<string, (chunk?: string | Uint8Array) => void> = {}
    vi.spyOn(process.stdin, "on").mockImplementation(((event: string, listener: (chunk?: string | Uint8Array) => void) => {
      listeners[event] = listener
      return process.stdin
    }) as any)
    const writes: string[] = []
    vi.spyOn(process.stdout, "write").mockImplementation(((chunk: string | Uint8Array) => {
      writes.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk))
      return true
    }) as any)
    const endSpy = vi.spyOn(process.stdout, "end").mockImplementation((() => process.stdout) as any)
    const previousExitCode = process.exitCode
    process.exitCode = undefined

    startSsrWorker({
      render: (page: any) => `<h1>${page.component}</h1>`,
    })

    expect(listeners.data).toBeDefined()
    expect(listeners.end).toBeDefined()

    const encoded = new TextEncoder().encode('{"id":20,"method":"render","params":{"page":{"component":"Café ☕"}}}\n')
    const splitAt = encoded.indexOf(0xe2) + 1
    listeners.data!(encoded.slice(0, splitAt))
    listeners.data!(encoded.slice(splitAt))
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(writes).toHaveLength(1)
    expect(JSON.parse(writes[0])).toEqual({ id: 20, result: { head: [], body: "<h1>Café ☕</h1>" } })
    expect(endSpy).not.toHaveBeenCalled()
    expect(process.exitCode).toBeUndefined()

    listeners.data!('{"id":21,"method":"ping"}')
    listeners.end!()
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(JSON.parse(writes[1])).toEqual({ id: 21, result: { status: "pong" } })
    expect(process.exitCode).toBe(0)
    expect(endSpy).toHaveBeenCalledTimes(1)
    process.exitCode = previousExitCode
  })

  it.each([undefined, "", "   "])("requires a configured ssrDir before loading dynamic entrypoints (%j)", async (ssrDir) => {
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "entry.mjs" } }, { ssrDir })).rejects.toThrow(
      "Dynamic SSR entrypoint loading requires a configured ssrDir",
    )
  })

  it("rejects dynamic entrypoint resolution when configured ssrDir does not exist or is not a directory", async () => {
    const baseDir = makeTempDir("litestar-ssr-badroot-")
    const missingDir = path.join(baseDir, "does-not-exist")
    const filePath = path.join(baseDir, "not-a-dir.mjs")
    fs.writeFileSync(filePath, "export default () => '<p>file</p>'\n", "utf8")

    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "entry.mjs" } }, { ssrDir: missingDir })).rejects.toThrow("Configured SSR directory does not exist")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "entry.mjs" } }, { ssrDir: filePath })).rejects.toThrow("Configured SSR directory does not exist")
  })

  it("loads valid dynamic entrypoints strictly inside ssrDir including internal symlinks", async () => {
    const ssrDir = makeTempDir("litestar-ssr-valid-")
    const nestedDir = path.join(ssrDir, "nested")
    fs.mkdirSync(nestedDir, { recursive: true })

    const defaultEntry = path.join(ssrDir, "entry.mjs")
    fs.writeFileSync(defaultEntry, "export default (page) => `<main>${page.component}</main>`\n", "utf8")

    const namedEntry = path.join(nestedDir, "named.mjs")
    fs.writeFileSync(namedEntry, 'export function render(page) { return { head: ["<title>SSR</title>"], body: `<section>${page.component}</section>` } }\n', "utf8")

    const dotDotPrefixedEntry = path.join(ssrDir, "..entry.mjs")
    fs.writeFileSync(dotDotPrefixedEntry, "export default (page) => `<article>${page.component}</article>`\n", "utf8")

    const internalSymlink = path.join(ssrDir, "alias-entry.mjs")
    fs.symlinkSync(defaultEntry, internalSymlink)

    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "entry.mjs", page: { component: "Home" } } }, { ssrDir })).resolves.toEqual({
      head: [],
      body: "<main>Home</main>",
    })
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "./nested/named.mjs", page: { component: "About" } } }, { ssrDir })).resolves.toEqual({
      head: ["<title>SSR</title>"],
      body: "<section>About</section>",
    })
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "..entry.mjs", page: { component: "Docs" } } }, { ssrDir })).resolves.toEqual({
      head: [],
      body: "<article>Docs</article>",
    })
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "alias-entry.mjs", page: { component: "Alias" } } }, { ssrDir })).resolves.toEqual({
      head: [],
      body: "<main>Alias</main>",
    })
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: defaultEntry, page: { component: "Abs" } } }, { ssrDir })).resolves.toEqual({
      head: [],
      body: "<main>Abs</main>",
    })
  })

  it.each([
    "",
    "   ",
    "entry.mjs\0.js",
    "file:///etc/passwd",
    "data:text/javascript,export default () => 'ok'",
    "http://127.0.0.1:8000/ssr.mjs",
    "https://example.com/ssr.mjs",
    "node:fs",
  ])("rejects invalid dynamic entrypoint %j", async (entrypoint) => {
    const ssrDir = makeTempDir("litestar-ssr-invalid-")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint } }, { ssrDir })).rejects.toThrow("Invalid SSR entrypoint")
  })

  it("blocks traversal, absolute paths outside ssrDir, root equality, sibling prefix paths, and symlink escapes", async () => {
    const parentDir = makeTempDir("litestar-ssr-escape-")
    const ssrDir = path.join(parentDir, "ssr")
    const siblingDir = path.join(parentDir, "ssr-other")
    const outsideDir = path.join(parentDir, "outside")
    fs.mkdirSync(ssrDir, { recursive: true })
    fs.mkdirSync(siblingDir, { recursive: true })
    fs.mkdirSync(outsideDir, { recursive: true })

    const outsideEntry = path.join(outsideDir, "outside.mjs")
    fs.writeFileSync(outsideEntry, 'export default () => "<p>outside</p>"\n', "utf8")
    const siblingEntry = path.join(siblingDir, "sibling.mjs")
    fs.writeFileSync(siblingEntry, 'export default () => "<p>sibling</p>"\n', "utf8")

    const fileSymlink = path.join(ssrDir, "escape-file.mjs")
    fs.symlinkSync(outsideEntry, fileSymlink)
    const dirSymlink = path.join(ssrDir, "escape-dir")
    fs.symlinkSync(outsideDir, dirSymlink)

    const outsideCases = ["../outside/outside.mjs", "nested/../../outside/outside.mjs", ".", ssrDir, outsideEntry, siblingEntry, "escape-file.mjs", "escape-dir/outside.mjs"]

    for (const entrypoint of outsideCases) {
      await expect(dispatchSsrRequest({ method: "render", params: { entrypoint } }, { ssrDir })).rejects.toThrow("SSR entrypoint is outside the configured SSR directory")
    }
  })

  it.each([
    { label: "missing token", token: undefined },
    { label: "empty token", token: "" },
    { label: "wrong token same length", token: "test-token-placeholdeX" },
    { label: "shorter token", token: "test-token" },
    { label: "longer token", token: "test-token-placeholder-extra" },
    { label: "trailing NUL byte", token: "test-token-placeholder\0" },
    { label: "non-string token", token: 123 as unknown as string },
  ])("enforces constant-time authToken verification before dispatching any method ($label)", async ({ token }) => {
    const options = {
      authToken: "test-token-placeholder",
      render: (page: any) => `<main>${page.component}</main>`,
      renderFragment: (params: Record<string, unknown>) => ({ html: `<aside>${params.component}</aside>` }),
    }

    await expect(dispatchSsrRequest({ method: "ping", token }, options)).rejects.toThrow("Unauthorized SSR request")
    await expect(dispatchSsrRequest({ method: "render", params: { page: { component: "Home" } }, token }, options)).rejects.toThrow("Unauthorized SSR request")
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card" }, token }, options)).rejects.toThrow("Unauthorized SSR request")
    await expect(dispatchSsrRequest({ method: "unknown", token }, options)).rejects.toThrow("Unauthorized SSR request")
  })

  it("allows requests with matching authToken and preserves unauthenticated stdio when authToken is omitted", async () => {
    const options = {
      authToken: "test-token-placeholder",
      render: (page: any) => `<main>${page.component}</main>`,
      renderFragment: (params: Record<string, unknown>) => ({ html: `<aside>${params.component}</aside>` }),
    }

    await expect(dispatchSsrRequest({ method: "ping", token: "test-token-placeholder" }, options)).resolves.toEqual({ status: "pong" })
    await expect(dispatchSsrRequest({ method: "render", params: { page: { component: "Home" } }, token: "test-token-placeholder" }, options)).resolves.toEqual({
      head: [],
      body: "<main>Home</main>",
    })
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card" }, token: "test-token-placeholder" }, options)).resolves.toEqual({
      html: "<aside>Card</aside>",
    })

    await expect(dispatchSsrRequest({ method: "ping" }, { authToken: "" })).resolves.toEqual({ status: "pong" })

    vi.spyOn(process.stdin, "on").mockImplementation(() => process.stdin)
    startSsrWorker(options)
    const dispatch = (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__ as (line: string) => Promise<string>
    expect(JSON.parse(await dispatch(JSON.stringify({ id: 1, method: "ping" })))).toEqual({
      id: 1,
      error: "Unauthorized SSR request",
    })
    expect(JSON.parse(await dispatch(JSON.stringify({ id: 2, method: "ping", token: "test-token-placeholder" })))).toEqual({
      id: 2,
      result: { status: "pong" },
    })
  })

  it("contains zero static node:* imports in ssr-worker.ts", () => {
    const workerSource = fs.readFileSync(path.resolve(import.meta.dirname, "../src/ssr-worker.ts"), "utf8")
    expect(workerSource).not.toMatch(/^\s*import\b[^;\n]*["']node:/m)
  })
})

describe("SSR worker CLI options and invocation", () => {
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__
    vi.restoreAllMocks()
    while (createdDirs.length > 0) {
      const dir = createdDirs.pop()
      if (dir) {
        fs.rmSync(dir, { recursive: true, force: true })
      }
    }
  })

  it("resolves ssrDir with precedence CLI > env > bridge ssrOutDir and authToken only from CLI > env", () => {
    const tempDir = makeTempDir("litestar-ssr-cli-opts-")
    const bridgePath = path.join(tempDir, ".litestar.json")
    writeBridgeConfigFile(bridgePath, {
      ssrOutDir: "/bridge/ssr",
      proxyToken: "test-bridge-proxy-token-placeholder",
    })

    expect(
      resolveSsrWorkerCliOptions(["--ssr-dir", "/cli/ssr", "--auth-token", "test-cli-token-placeholder"], {
        LITESTAR_SSR_DIR: "/env/ssr",
        LITESTAR_SSR_AUTH_TOKEN: "test-env-token-placeholder",
        LITESTAR_VITE_CONFIG_PATH: bridgePath,
      }),
    ).toEqual({
      ssrDir: "/cli/ssr",
      authToken: "test-cli-token-placeholder",
    })

    expect(
      resolveSsrWorkerCliOptions(["--ssr-dir=/cli-eq/ssr", "--auth-token=test-cli-eq-token-placeholder"], {
        LITESTAR_SSR_DIR: "/env/ssr",
        LITESTAR_SSR_AUTH_TOKEN: "test-env-token-placeholder",
        LITESTAR_VITE_CONFIG_PATH: bridgePath,
      }),
    ).toEqual({
      ssrDir: "/cli-eq/ssr",
      authToken: "test-cli-eq-token-placeholder",
    })

    expect(
      resolveSsrWorkerCliOptions([], {
        LITESTAR_SSR_DIR: "/env/ssr",
        LITESTAR_SSR_AUTH_TOKEN: "test-env-token-placeholder",
        LITESTAR_VITE_CONFIG_PATH: bridgePath,
      }),
    ).toEqual({
      ssrDir: "/env/ssr",
      authToken: "test-env-token-placeholder",
    })

    expect(
      resolveSsrWorkerCliOptions([], {
        LITESTAR_VITE_CONFIG_PATH: bridgePath,
      }),
    ).toEqual({
      ssrDir: "/bridge/ssr",
    })

    expect(
      resolveSsrWorkerCliOptions(["--", "--ssr-dir", "/ignored", "--auth-token", "ignored"], {
        LITESTAR_VITE_CONFIG_PATH: path.join(tempDir, "missing.litestar.json"),
      }),
    ).toEqual({})
  })

  it("canonicalizes symlinked CLI bin invocations when deciding whether to auto-start", async () => {
    const tempDir = makeTempDir("litestar-ssr-cli-bin-")
    const binDir = path.join(tempDir, "bin")
    const ssrDir = path.join(tempDir, "ssr")
    fs.mkdirSync(binDir, { recursive: true })
    fs.mkdirSync(ssrDir, { recursive: true })

    const entryPath = path.join(ssrDir, "entry.mjs")
    fs.writeFileSync(entryPath, "export default (page) => `<p>${page.component}</p>`\n", "utf8")

    const realCliPath = path.resolve(import.meta.dirname, "../src/ssr-worker-cli.ts")
    const symlinkBinPath = path.join(binDir, "litestar-vite-ssr-worker")
    fs.symlinkSync(realCliPath, symlinkBinPath)

    expect(isDirectCliInvocation(symlinkBinPath, pathToFileURL(realCliPath).href)).toBe(true)
    expect(isDirectCliInvocation(path.join(tempDir, "other.js"), pathToFileURL(realCliPath).href)).toBe(false)
    expect(isDirectCliInvocation(undefined, pathToFileURL(realCliPath).href)).toBe(false)
    expect(isDirectCliInvocation(path.join(tempDir, "virtual-cli.js"), pathToFileURL(path.join(tempDir, "virtual-cli.js")).href)).toBe(true)

    const previousArgv = process.argv
    try {
      vi.spyOn(process.stdin, "on").mockImplementation(() => process.stdin)
      process.argv = [previousArgv[0], symlinkBinPath, "--ssr-dir", ssrDir, "--auth-token", "test-token-placeholder"]
      vi.resetModules()
      await import("../src/ssr-worker-cli.js")

      const dispatch = (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__ as ((line: string) => Promise<string>) | undefined
      expect(typeof dispatch).toBe("function")

      const unauthorized = JSON.parse(await dispatch!(JSON.stringify({ id: 1, method: "render", params: { entrypoint: "entry.mjs", page: { component: "Symlink" } } })))
      expect(unauthorized).toEqual({ id: 1, error: "Unauthorized SSR request" })

      const rendered = JSON.parse(
        await dispatch!(
          JSON.stringify({
            id: 2,
            method: "render",
            token: "test-token-placeholder",
            params: { entrypoint: "entry.mjs", page: { component: "Symlink" } },
          }),
        ),
      )
      expect(rendered).toEqual({ id: 2, result: { head: [], body: "<p>Symlink</p>" } })
    } finally {
      process.argv = previousArgv
    }
  })
})
