import fs from "node:fs"
import path from "node:path"
import type { Plugin, ViteDevServer } from "vite"
import { createServerModuleRunner, isRunnableDevEnvironment, normalizePath } from "vite"
import { renderFragment } from "./fragments/renderer.js"
import { readBridgeConfig, verifyBridgeRequest } from "./shared/bridge-schema.js"
import { manageSsrCache } from "./shared/ssr-cache.js"
import type { DevSsrOptions, SsrRenderRequest, SsrRenderResponse } from "./shared/ssr-types.js"

class SsrValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "SsrValidationError"
  }
}

function isWithinRoots(roots: string[], targetPath: string): boolean {
  return roots.some((directory) => {
    const relative = path.relative(directory, targetPath)
    return relative !== "" && relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
  })
}

function resolveComponent(root: string, roots: string[], component: string, logError?: (msg: string) => void): string {
  if (
    component.includes("\\") ||
    component.includes("\0") ||
    component.includes("?") ||
    component.includes("#") ||
    component.startsWith("/@") ||
    /^[a-z][a-z\d+.-]*:/i.test(component)
  ) {
    throw new SsrValidationError("Invalid fragment component path.")
  }
  if (![".tsx", ".jsx", ".vue", ".svelte", ".astro"].includes(path.extname(component).toLowerCase())) {
    throw new SsrValidationError("Unsupported fragment component extension.")
  }
  const candidate = path.resolve(root, component)
  if (!isWithinRoots(roots, candidate)) {
    throw new SsrValidationError("Fragment component is outside the configured component roots.")
  }
  let resolved: string
  try {
    resolved = fs.realpathSync(candidate)
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err)
    logError?.(`[litestar-vite] Failed to resolve fragment component '${component}': ${detail}`)
    throw new SsrValidationError("Fragment component could not be resolved.")
  }
  if (!isWithinRoots(roots, resolved)) {
    throw new SsrValidationError("Fragment component is outside the configured component roots.")
  }
  return normalizePath(resolved)
}

export function litestarViteSsrPlugin(options: DevSsrOptions = {}): Plugin {
  const endpoint = options.endpoint ?? "/__litestar_ssr__"

  return {
    name: "litestar-vite:dev-ssr",
    apply: "serve",
    configureServer(server: ViteDevServer) {
      if (!options.entrypoint && !options.componentRoots?.length) return
      const rawRoot = server.config.root ?? process.cwd()
      let canonicalRoot: string
      try {
        canonicalRoot = fs.realpathSync(rawRoot)
      } catch {
        canonicalRoot = path.resolve(rawRoot)
      }
      const entrypoint = options.entrypoint ? normalizePath(fs.realpathSync(path.resolve(canonicalRoot, options.entrypoint))) : undefined
      const componentRoots = (options.componentRoots ?? []).map((directory) => fs.realpathSync(path.resolve(canonicalRoot, directory)))
      const ssrEnv = server.environments?.ssr
      if (!ssrEnv) {
        server.config?.logger?.warn?.("[litestar-vite] server.environments.ssr is not configured. Vite 7+ Environment API is required for ModuleRunner dev SSR.")
        return
      }

      const ownsRunner = options.hmr === false || !isRunnableDevEnvironment(ssrEnv)
      const runner = ownsRunner
        ? createServerModuleRunner(ssrEnv, {
            hmr: options.hmr === false ? false : undefined,
          })
        : ssrEnv.runner

      const cacheManager = manageSsrCache(runner, server)

      const cleanup = () => {
        cacheManager.dispose()
        if (ownsRunner) {
          void runner.close()
        }
      }

      server.httpServer?.once("close", cleanup)

      const MAX_BODY_BYTES = 10 * 1024 * 1024

      server.middlewares.use(endpoint, async (req, res, next) => {
        const subPath = req.url?.split("?")[0] ?? ""
        if (req.method !== "POST") return next()
        const expectedToken = options.proxyToken ?? readBridgeConfig()?.proxyToken ?? null
        const auth = verifyBridgeRequest(req, expectedToken)
        if (!auth.ok) {
          res.statusCode = auth.statusCode
          res.end(auth.message)
          return
        }
        if (subPath === "/invalidate" || subPath === "/invalidate/") {
          cacheManager.clearAll()
          res.statusCode = 200
          res.setHeader("Content-Type", "application/json; charset=utf-8")
          res.end(JSON.stringify({ success: true, message: "SSR cache cleared" }))
          return
        }

        if (subPath !== "" && subPath !== "/") return next()

        const chunks: Buffer[] = []
        let totalBytes = 0
        let aborted = false
        req.on("error", () => {
          aborted = true
        })
        req.on("data", (chunk: Buffer) => {
          if (aborted) return
          totalBytes += chunk.length
          if (totalBytes > MAX_BODY_BYTES) {
            aborted = true
            res.statusCode = 413
            res.setHeader("Content-Type", "application/json; charset=utf-8")
            res.end(JSON.stringify({ error: { message: "SSR request payload too large" } }))
            req.destroy()
            return
          }
          chunks.push(chunk)
        })
        req.on("end", async () => {
          if (aborted) return
          let requestId: number | string | undefined
          try {
            const rawBody = Buffer.concat(chunks).toString("utf-8")
            const payload: SsrRenderRequest = rawBody ? JSON.parse(rawBody) : {}
            if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
              throw new SsrValidationError("Invalid SSR request.")
            }
            requestId = payload.id
            if ("entrypoint" in payload) {
              throw new SsrValidationError("SSR entrypoints must be configured on the server.")
            }

            if (payload.method === "render_fragment" || payload.type === "fragment") {
              const params = (payload.params ?? payload) as Record<string, unknown>
              const rawComponent = typeof params.component === "string" ? params.component : ""
              if (!rawComponent) {
                throw new SsrValidationError("render_fragment requires a 'component' parameter.")
              }
              const props = (typeof params.props === "object" && params.props !== null ? params.props : {}) as Record<string, unknown>
              const mode = params.mode === "island" ? "island" : "static"
              const resolvedComponent = resolveComponent(canonicalRoot, componentRoots, rawComponent, (msg) => {
                server.config?.logger?.error?.(msg)
              })
              const fragmentRes = await renderFragment({ componentPath: rawComponent, props, mode, clientEntry: options.clientEntry }, () => runner.import(resolvedComponent))
              const response: SsrRenderResponse = {
                id: payload.id,
                result: { ...fragmentRes },
              }
              res.statusCode = 200
              res.setHeader("Content-Type", "application/json; charset=utf-8")
              res.end(JSON.stringify(response))
              return
            }

            if (!entrypoint) throw new SsrValidationError("SSR rendering requires a configured entrypoint.")
            const mod = await runner.import(entrypoint)
            const renderFn = typeof mod.default === "function" ? mod.default : typeof mod.render === "function" ? mod.render : null
            if (!renderFn) {
              throw new Error(`Module '${entrypoint}' does not export a default function or 'render' function.`)
            }

            const paramsObj = payload.params as Record<string, unknown> | undefined
            const pageOrProps = payload.page ?? (paramsObj?.page as Record<string, unknown> | undefined) ?? paramsObj ?? payload.props ?? {}
            const result = await renderFn(pageOrProps)

            const response: SsrRenderResponse = {
              id: payload.id,
              result: typeof result === "string" ? { head: [], body: result } : result,
            }

            res.statusCode = 200
            res.setHeader("Content-Type", "application/json; charset=utf-8")
            res.end(JSON.stringify(response))
          } catch (err: unknown) {
            const errorObj = err instanceof Error ? err : new Error(String(err))
            server.ssrFixStacktrace(errorObj)
            const detail =
              errorObj.stack && errorObj.stack.includes(errorObj.message) ? errorObj.stack : errorObj.stack ? `${errorObj.message}\n${errorObj.stack}` : errorObj.message
            server.config?.logger?.error?.(`[litestar-vite] ${detail}`)
            const response: SsrRenderResponse = {
              id: requestId,
              error: err instanceof SsrValidationError ? { message: err.message, name: err.name } : { message: "SSR render error" },
            }
            res.statusCode = 500
            res.setHeader("Content-Type", "application/json; charset=utf-8")
            res.end(JSON.stringify(response))
          }
        })
      })
    },
  }
}
