import fs from "node:fs"
import net from "node:net"
import readline from "node:readline"
import { PassThrough } from "node:stream"

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
    process.stderr.write(`[ssr-worker] Invalid NDJSON payload: ${detail}\n`)
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
    writeFn(JSON.stringify(response) + "\n")
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    const response: IPCResponseError = { id: requestId, error: errorMsg }
    writeFn(JSON.stringify(response) + "\n")
  }
}

async function handleHttpPayload(bodyStr: string, socket: net.Socket): Promise<void> {
  let msg: IPCRequest = {}
  try {
    msg = bodyStr ? (JSON.parse(bodyStr) as IPCRequest) : {}
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    const errBody = JSON.stringify({ id: null, error: errorMsg })
    socket.write(
      `HTTP/1.1 400 Bad Request\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${Buffer.byteLength(errBody)}\r\nConnection: close\r\n\r\n${errBody}`,
    )
    socket.end()
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
    const resBody = JSON.stringify(response)
    socket.write(`HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${Buffer.byteLength(resBody)}\r\nConnection: close\r\n\r\n${resBody}`)
    socket.end()
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    const response: IPCResponseError = { id: requestId, error: errorMsg }
    const resBody = JSON.stringify(response)
    socket.write(
      `HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${Buffer.byteLength(resBody)}\r\nConnection: close\r\n\r\n${resBody}`,
    )
    socket.end()
  }
}

function main(): void {
  const args = process.argv.slice(2)
  let mode: "stdio" | "socket" | "port" = "stdio"
  let socketPath: string | null = null
  let port: number | null = null

  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (arg === "--stdio") {
      mode = "stdio"
    } else if (arg === "--socket" && i + 1 < args.length) {
      mode = "socket"
      socketPath = args[++i]
    } else if (arg === "--port" && i + 1 < args.length) {
      mode = "port"
      port = Number.parseInt(args[++i], 10)
    }
  }

  if (!socketPath && process.env.INERTIA_SSR_SOCKET) {
    mode = "socket"
    socketPath = process.env.INERTIA_SSR_SOCKET
  }
  if (!port && process.env.INERTIA_SSR_PORT) {
    mode = "port"
    port = Number.parseInt(process.env.INERTIA_SSR_PORT, 10)
  }

  if (mode === "stdio") {
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
  } else if (mode === "socket" && socketPath) {
    try {
      if (fs.existsSync(socketPath)) {
        fs.unlinkSync(socketPath)
      }
    } catch {
      // Ignore cleanup error
    }

    const server = net.createServer((socket) => {
      const rl = readline.createInterface({
        input: socket,
        terminal: false,
        crlfDelay: Number.POSITIVE_INFINITY,
      })

      rl.on("line", (line: string) => {
        void processLine(line, (data: string) => {
          socket.write(data)
        })
      })
    })

    const cleanup = () => {
      try {
        if (socketPath && fs.existsSync(socketPath)) {
          fs.unlinkSync(socketPath)
        }
      } catch {
        // Ignore cleanup error
      }
      process.exit(0)
    }

    process.on("SIGINT", cleanup)
    process.on("SIGTERM", cleanup)
    process.on("exit", () => {
      try {
        if (socketPath && fs.existsSync(socketPath)) {
          fs.unlinkSync(socketPath)
        }
      } catch {
        // Ignore
      }
    })

    server.listen(socketPath, () => {
      process.stderr.write(`[ssr-worker] Listening on Unix socket: ${socketPath}\n`)
    })
  } else if (mode === "port" && port) {
    const server = net.createServer((socket) => {
      let initialized = false
      let buffer = Buffer.alloc(0)

      socket.on("data", (chunk: Buffer) => {
        if (!initialized) {
          buffer = Buffer.concat([buffer, chunk])
          const raw = buffer.toString("latin1")
          if (raw.startsWith("POST ") || raw.startsWith("GET ") || raw.startsWith("OPTIONS ")) {
            const headerEnd = buffer.indexOf("\r\n\r\n")
            if (headerEnd !== -1) {
              const headerPart = buffer.subarray(0, headerEnd).toString("utf-8")
              let contentLength = 0
              for (const headerLine of headerPart.split("\r\n")) {
                if (headerLine.toLowerCase().startsWith("content-length:")) {
                  contentLength = Number.parseInt(headerLine.split(":")[1].trim(), 10) || 0
                  break
                }
              }
              const bodyBytes = buffer.subarray(headerEnd + 4)
              if (bodyBytes.length >= contentLength) {
                initialized = true
                const bodyStr = bodyBytes.subarray(0, contentLength).toString("utf-8")
                void handleHttpPayload(bodyStr, socket)
              }
            }
            return
          }

          initialized = true
          const passThrough = new PassThrough()
          passThrough.write(buffer)
          socket.pipe(passThrough)

          const rl = readline.createInterface({
            input: passThrough,
            terminal: false,
            crlfDelay: Number.POSITIVE_INFINITY,
          })

          rl.on("line", (line: string) => {
            void processLine(line, (data: string) => {
              socket.write(data)
            })
          })
        }
      })
    })

    server.listen(port, "127.0.0.1", () => {
      process.stderr.write(`[ssr-worker] Listening on TCP port: ${port}\n`)
    })
  }
}

main()
