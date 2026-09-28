import fs from "node:fs"
import path from "node:path"
import type { Plugin, ViteDevServer } from "vite"
import { createServerModuleRunner, isRunnableDevEnvironment, normalizePath } from "vite"
import { renderFragment } from "./fragments/renderer.js"
import { manageSsrCache } from "./shared/ssr-cache.js"
import type { DevSsrOptions, SsrRenderRequest, SsrRenderResponse } from "./shared/ssr-types.js"

function resolveComponent(root: string, roots: string[], component: string): string {
  if (
    component.includes("\\") ||
    component.includes("\0") ||
    component.includes("?") ||
    component.includes("#") ||
    component.startsWith("/@") ||
    /^[a-z][a-z\d+.-]*:/i.test(component)
  ) {
    throw new Error("Invalid fragment component path.")
  }
  if (![".tsx", ".jsx", ".vue", ".svelte", ".astro"].includes(path.extname(component).toLowerCase())) {
    throw new Error("Unsupported fragment component extension.")
  }
  const resolved = fs.realpathSync(path.resolve(root, component))
  const allowed = roots.some((directory) => {
    const relative = path.relative(directory, resolved)
    return relative !== "" && relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
  })
  if (!allowed) throw new Error("Fragment component is outside the configured component roots.")
  return normalizePath(resolved)
}

export function litestarViteSsrPlugin(options: DevSsrOptions = {}): Plugin {
  const endpoint = options.endpoint ?? "/__litestar_ssr__"

  return {
    name: "litestar-vite:dev-ssr",
    apply: "serve",
    configureServer(server: ViteDevServer) {
      if (!options.entrypoint && !options.componentRoots?.length) return
      const root = server.config.root ?? process.cwd()
      const entrypoint = options.entrypoint ? normalizePath(fs.realpathSync(path.resolve(root, options.entrypoint))) : undefined
      const componentRoots = (options.componentRoots ?? []).map((directory) => fs.realpathSync(path.resolve(root, directory)))
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
        // This endpoint is backend IPC. Browser requests must never execute server modules.
        if (req.headers.origin !== undefined || req.headers["sec-fetch-site"] !== undefined) {
          res.statusCode = 403
          res.end("Browser requests are not allowed on the SSR endpoint")
          return
        }
        if (req.headers["content-type"]?.split(";")[0].trim().toLowerCase() !== "application/json") {
          res.statusCode = 415
          res.end("Content-Type must be application/json")
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
            if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error("Invalid SSR request.")
            requestId = payload.id
            if ("entrypoint" in payload) throw new Error("SSR entrypoints must be configured on the server.")

            if (payload.method === "render_fragment" || payload.type === "fragment") {
              const params = (payload.params ?? payload) as Record<string, unknown>
              const rawComponent = typeof params.component === "string" ? params.component : ""
              if (!rawComponent) {
                throw new Error("render_fragment requires a 'component' parameter.")
              }
              const props = (typeof params.props === "object" && params.props !== null ? params.props : {}) as Record<string, unknown>
              const mode = params.mode === "island" ? "island" : "static"
              const resolvedComponent = resolveComponent(root, componentRoots, rawComponent)
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

            if (!entrypoint) throw new Error("SSR rendering requires a configured entrypoint.")
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
          } catch (err: any) {
            server.ssrFixStacktrace(err)
            const response: SsrRenderResponse = {
              id: requestId,
              error: {
                message: err?.message || String(err),
                stack: err?.stack,
                name: err?.name,
              },
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
