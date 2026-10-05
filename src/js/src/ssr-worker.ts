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
  const dispatchLine = async (line: string): Promise<string> => {
    const trimmed = line.trim()
    if (!trimmed) {
      return ""
    }
    let id: number | string | null = null
    try {
      const request = JSON.parse(trimmed) as IPCRequest
      if (typeof request !== "object" || request === null || Array.isArray(request)) {
        throw new Error("Invalid SSR request")
      }
      id = request.id ?? null
      const result = await dispatchSsrRequest(request, options)
      return JSON.stringify({ id, result })
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      return JSON.stringify({ id, error: message })
    }
  }

  ;(globalThis as Record<string, unknown>).__litestar_ssr_dispatch__ = dispatchLine

  if (typeof process !== "undefined" && process.stdin && typeof process.stdin.on === "function") {
    if (typeof process.stdin.setEncoding === "function") {
      process.stdin.setEncoding("utf8")
    }
    const decoder = new TextDecoder("utf-8")
    let buffer = ""
    let inflight = 0
    let ended = false

    const exitIfDrained = (): void => {
      if (ended && inflight === 0 && typeof process.exit === "function") {
        process.exit(0)
      }
    }

    const handleLine = (line: string): void => {
      inflight += 1
      void dispatchLine(line)
        .then((out) => {
          if (out) {
            process.stdout.write(`${out}\n`)
          }
        })
        .finally(() => {
          inflight -= 1
          exitIfDrained()
        })
    }

    process.stdin.on("data", (chunk: string | Uint8Array) => {
      buffer += typeof chunk === "string" ? chunk : decoder.decode(chunk, { stream: true })
      let newlineIdx = buffer.indexOf("\n")
      while (newlineIdx !== -1) {
        const line = buffer.slice(0, newlineIdx).replace(/\r$/, "")
        buffer = buffer.slice(newlineIdx + 1)
        newlineIdx = buffer.indexOf("\n")
        handleLine(line)
      }
    })

    const onEnd = (): void => {
      if (ended) return
      ended = true
      buffer += decoder.decode()
      if (buffer.trim()) {
        handleLine(buffer)
        buffer = ""
      }
      exitIfDrained()
    }
    process.stdin.on("end", onEnd)
    process.stdin.on("close", onEnd)
  }
}
