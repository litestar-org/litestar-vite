import readline from "node:readline"

export interface SsrWorkerOptions {
  render?: (page: any) => unknown | Promise<unknown>
  renderFragment?: (params: Record<string, unknown>) => unknown | Promise<unknown>
}

export interface IPCRequest {
  id?: number | string
  method?: string
  params?: Record<string, unknown>
  payload?: Record<string, unknown>
  [key: string]: unknown
}

/** Dispatch one request, preserving rendering errors for the transport's fallback policy. */
export async function dispatchSsrRequest(request: IPCRequest, options: SsrWorkerOptions = {}): Promise<unknown> {
  const params = request.params ?? request.payload ?? request
  switch (request.method ?? "render") {
    case "ping":
      return { status: "pong" }
    case "render_fragment": {
      if (options.renderFragment) return options.renderFragment(params)
      throw new Error("Fragment rendering requires a configured compiled component registry")
    }
    case "render": {
      let render = options.render
      if (!render && typeof params.entrypoint === "string") {
        const mod = await import(/* @vite-ignore */ params.entrypoint)
        render = typeof mod.default === "function" ? mod.default : typeof mod.render === "function" ? mod.render : undefined
      }
      if (!render) throw new Error("SSR requires a configured render function or an entrypoint exporting a render function")
      const result = await render(params.page ?? params)
      return typeof result === "string" ? { head: [], body: result } : result
    }
    default:
      throw new Error(`Unsupported method: ${request.method}`)
  }
}

/** Start the shared newline-delimited JSON RPC worker for an application's SSR entry. */
export function startSsrWorker(options: SsrWorkerOptions = {}): void {
  const rl = readline.createInterface({ input: process.stdin, terminal: false, crlfDelay: Number.POSITIVE_INFINITY })
  rl.on("line", (line: string) => {
    if (!line.trim()) return
    void (async () => {
      let id: number | string | null = null
      try {
        const request = JSON.parse(line) as IPCRequest
        if (typeof request !== "object" || request === null || Array.isArray(request)) throw new Error("Invalid SSR request")
        id = request.id ?? null
        const result = await dispatchSsrRequest(request, options)
        process.stdout.write(`${JSON.stringify({ id, result })}\n`)
      } catch (error) {
        process.stdout.write(`${JSON.stringify({ id, error: error instanceof Error ? error.message : String(error) })}\n`)
      }
    })()
  })
}
