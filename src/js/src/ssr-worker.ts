import readline from "node:readline"
import { renderFragment } from "./fragments/renderer.js"

interface IPCRequest {
  id?: number | string
  method?: string
  params?: Record<string, unknown>
  payload?: Record<string, unknown>
  page?: {
    component: string
    props: Record<string, unknown>
    url: string
    version?: string
  }
  component?: string
  props?: Record<string, unknown>
  mode?: "static" | "island"
  entrypoint?: string
}

interface IPCResponseSuccess {
  id?: number | string
  result: unknown
}

interface IPCResponseError {
  id?: number | string
  error: string
}

async function handleRender(method: string, params?: Record<string, unknown>): Promise<unknown> {
  switch (method) {
    case "ping":
      return { status: "pong", timestamp: Date.now() }
    case "render_fragment": {
      const componentPath = typeof params?.component === "string" ? params.component : ""
      if (!componentPath) {
        throw new Error("render_fragment requires a 'component' parameter")
      }
      const props = (typeof params?.props === "object" && params?.props !== null ? params.props : {}) as Record<string, unknown>
      const mode = params?.mode === "island" ? "island" : "static"
      return await renderFragment({ componentPath, props, mode })
    }
    case "render": {
      if (typeof params?.entrypoint === "string") {
        try {
          const mod = (await import(params.entrypoint)) as Record<string, unknown>
          const renderFn =
            typeof mod.default === "function"
              ? (mod.default as (payload: unknown) => unknown)
              : typeof mod.render === "function"
                ? (mod.render as (payload: unknown) => unknown)
                : null
          if (renderFn) {
            const pageOrProps = params.page ?? params.props ?? params
            const res = await renderFn(pageOrProps)
            return typeof res === "string" ? { head: [], body: res } : res
          }
        } catch {
          // Fall back to default rendered output on import or execution error
        }
      }

      let component = "unknown"
      if (typeof params?.component === "string") {
        component = params.component
      } else if (
        params &&
        typeof params.page === "object" &&
        params.page !== null &&
        "component" in params.page &&
        typeof (params.page as Record<string, unknown>).component === "string"
      ) {
        component = (params.page as Record<string, unknown>).component as string
      }
      return { head: [], body: `<!--rendered:${component}-->` }
    }
    default:
      throw new Error(`Unsupported method: ${method}`)
  }
}

async function processLine(line: string, writeFn: (data: string) => void): Promise<void> {
  const trimmed = line.trim()
  if (!trimmed) {
    return
  }

  let msg: IPCRequest
  try {
    msg = JSON.parse(trimmed) as IPCRequest
  } catch (err: unknown) {
    const detail = err instanceof Error ? err.message : String(err)
    process.stderr.write(`[ssr-worker] Invalid JSON payload: ${detail}\n`)
    return
  }

  const requestId = msg.id ?? 0
  const method = msg.method ?? "render"
  const params = msg.params ??
    msg.payload ?? {
      component: msg.component,
      props: msg.props,
      page: msg.page,
      entrypoint: msg.entrypoint,
    }

  try {
    const result = await handleRender(method, params as Record<string, unknown>)
    const response: IPCResponseSuccess = { id: requestId, result }
    writeFn(`${JSON.stringify(response)}\n`)
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    const response: IPCResponseError = { id: requestId, error: errorMsg }
    writeFn(`${JSON.stringify(response)}\n`)
  }
}

function main(): void {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
    crlfDelay: Number.POSITIVE_INFINITY,
  })

  rl.on("line", (line: string) => {
    void processLine(line, (data: string) => {
      process.stdout.write(data)
    })
  })

  rl.on("close", () => {
    process.exit(0)
  })

  process.stdin.on("end", () => {
    process.exit(0)
  })

  process.on("SIGINT", () => process.exit(0))
  process.on("SIGTERM", () => process.exit(0))
}

main()
