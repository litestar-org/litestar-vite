import { afterEach, describe, expect, it, vi } from "vitest"
import { dispatchSsrRequest, startSsrWorker } from "../src/ssr-worker.js"

describe("SSR worker dispatch", () => {
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).__litestar_ssr_dispatch__
    vi.restoreAllMocks()
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
    await expect(dispatchSsrRequest({ method: "render" })).rejects.toThrow("SSR requires")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "missing-render-module" } })).rejects.toThrow("missing-render-module")
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
})
