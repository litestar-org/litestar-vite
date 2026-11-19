export interface SsrWorkerOptions {
  render?: (page: any) => unknown | Promise<unknown>
  renderFragment?: (params: Record<string, unknown>) => unknown | Promise<unknown>
  ssrDir?: string
  authToken?: string
}

export interface IPCRequest {
  id?: number | string
  method?: string
  params?: Record<string, unknown>
  payload?: Record<string, unknown>
  token?: string
  [key: string]: unknown
}

const URL_SCHEME_RE = /^[a-z][a-z\d+.-]{1,}:/i

function constantTimeEqual(provided: string, expected: string): boolean {
  const encoder = new TextEncoder()
  const a = encoder.encode(provided)
  const b = encoder.encode(expected)
  const length = Math.max(a.length, b.length)
  let diff = a.length ^ b.length
  for (let i = 0; i < length; i += 1) {
    diff |= (a[i] ?? 0) ^ (b[i] ?? 0)
  }
  return diff === 0
}

function isPathInsideDirectory(
  pathModule: { relative(from: string, to: string): string; isAbsolute(filePath: string): boolean; sep: string },
  rootDir: string,
  targetPath: string,
): boolean {
  const relative = pathModule.relative(rootDir, targetPath)
  return relative.length > 0 && relative !== ".." && !relative.startsWith(`..${pathModule.sep}`) && !pathModule.isAbsolute(relative)
}

async function resolveDynamicEntrypointUrl(entrypoint: string, ssrDir: string | undefined): Promise<string> {
  if (typeof ssrDir !== "string" || ssrDir.trim().length === 0) {
    throw new Error("Dynamic SSR entrypoint loading requires a configured ssrDir")
  }
  const trimmedEntrypoint = entrypoint.trim()
  if (trimmedEntrypoint.length === 0 || entrypoint.includes("\0") || URL_SCHEME_RE.test(trimmedEntrypoint)) {
    throw new Error("Invalid SSR entrypoint")
  }

  const [fs, path, url] = await Promise.all([import("node:fs"), import("node:path"), import("node:url")])
  const resolvedRoot = path.resolve(ssrDir)
  let canonicalRoot: string
  try {
    canonicalRoot = fs.realpathSync(resolvedRoot)
    if (!fs.statSync(canonicalRoot).isDirectory()) {
      throw new Error("Configured SSR directory does not exist")
    }
  } catch {
    throw new Error("Configured SSR directory does not exist")
  }

  const candidatePath = path.resolve(canonicalRoot, entrypoint)
  if (!isPathInsideDirectory(path, canonicalRoot, candidatePath) && !isPathInsideDirectory(path, resolvedRoot, candidatePath)) {
    throw new Error("SSR entrypoint is outside the configured SSR directory")
  }

  let canonicalEntrypoint: string
  try {
    canonicalEntrypoint = fs.realpathSync(candidatePath)
  } catch {
    throw new Error("SSR entrypoint could not be resolved")
  }

  if (!isPathInsideDirectory(path, canonicalRoot, canonicalEntrypoint)) {
    throw new Error("SSR entrypoint is outside the configured SSR directory")
  }

  try {
    if (!fs.statSync(canonicalEntrypoint).isFile()) {
      throw new Error("SSR entrypoint could not be resolved")
    }
  } catch {
    throw new Error("SSR entrypoint could not be resolved")
  }

  return url.pathToFileURL(canonicalEntrypoint).href
}

/** Dispatch one request, preserving rendering errors for the transport's fallback policy. */
export async function dispatchSsrRequest(request: IPCRequest, options: SsrWorkerOptions = {}): Promise<unknown> {
  if (typeof options.authToken === "string" && options.authToken.length > 0) {
    if (typeof request.token !== "string" || !constantTimeEqual(request.token, options.authToken)) {
      throw new Error("Unauthorized SSR request")
    }
  }
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
        const entrypointUrl = await resolveDynamicEntrypointUrl(params.entrypoint, options.ssrDir)
        const mod = await import(/* @vite-ignore */ entrypointUrl)
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
      if (ended && inflight === 0) {
        process.exitCode = 0
        if (typeof process.stdout.end === "function") {
          process.stdout.end()
        }
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
