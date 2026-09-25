import type { Plugin, ViteDevServer } from "vite"
import { createServerModuleRunner } from "vite"
import { renderFragment } from "./fragments/renderer.js"
import { manageSsrCache } from "./shared/ssr-cache.js"
import type { DevSsrOptions, SsrRenderRequest, SsrRenderResponse } from "./shared/ssr-types.js"

export function litestarViteSsrPlugin(options: DevSsrOptions = {}): Plugin {
  const endpoint = options.endpoint ?? "/__litestar_ssr__"
  const defaultEntrypoint = options.entrypoint ?? "resources/ssr.tsx"

  return {
    name: "litestar-vite:dev-ssr",
    apply: "serve",
    configureServer(server: ViteDevServer) {
      if (!server.environments?.ssr) {
        server.config.logger.warn("[litestar-vite] server.environments.ssr is not configured. Vite 6+ Environment API is required for ModuleRunner dev SSR.")
        return
      }

      const runner = createServerModuleRunner(server.environments.ssr, {
        hmr: options.hmr === false ? false : undefined,
      })

      const cacheManager = manageSsrCache(runner, server)

      const cleanup = () => {
        cacheManager.dispose()
        void runner.close()
      }

      server.httpServer?.on("close", cleanup)

      server.middlewares.use(endpoint, async (req, res, next) => {
        const subPath = req.url?.split("?")[0] ?? ""
        if (subPath === "/invalidate" || subPath === "/invalidate/") {
          if (req.method !== "POST") {
            res.statusCode = 405
            res.end("Method Not Allowed")
            return
          }
          cacheManager.clearAll()
          res.statusCode = 200
          res.setHeader("Content-Type", "application/json; charset=utf-8")
          res.end(JSON.stringify({ success: true, message: "SSR cache cleared" }))
          return
        }

        if (req.method !== "POST") {
          return next()
        }

        const chunks: Buffer[] = []
        req.on("data", (chunk: Buffer) => chunks.push(chunk))
        req.on("end", async () => {
          let requestId: number | string | undefined
          try {
            const rawBody = Buffer.concat(chunks).toString("utf-8")
            const payload: SsrRenderRequest = rawBody ? JSON.parse(rawBody) : {}
            requestId = payload.id

            if (payload.method === "render_fragment" || payload.type === "fragment") {
              const params = (payload.params ?? payload) as Record<string, unknown>
              const rawComponent = typeof params.component === "string" ? params.component : ""
              if (!rawComponent) {
                throw new Error("render_fragment requires a 'component' parameter.")
              }
              const props = (typeof params.props === "object" && params.props !== null ? params.props : {}) as Record<string, unknown>
              const mode = params.mode === "island" ? "island" : "static"
              const fragmentRes = await renderFragment({ componentPath: rawComponent, props, mode }, (spec: string) => {
                const normalized = spec.replace(/\\/g, "/")
                const resolved = normalized.startsWith("/") ? normalized : `/${normalized}`
                return runner.import(resolved)
              })
              const response: SsrRenderResponse = {
                id: payload.id,
                result: { ...fragmentRes },
              }
              res.statusCode = 200
              res.setHeader("Content-Type", "application/json; charset=utf-8")
              res.end(JSON.stringify(response))
              return
            }

            const rawEntry = payload.entrypoint ?? defaultEntrypoint
            const normalizedEntry = rawEntry.replace(/\\/g, "/")
            const resolvedEntry = normalizedEntry.startsWith("/") ? normalizedEntry : `/${normalizedEntry}`

            const mod = await runner.import(resolvedEntry)
            const renderFn = typeof mod.default === "function" ? mod.default : typeof mod.render === "function" ? mod.render : null
            if (!renderFn) {
              throw new Error(`Module '${resolvedEntry}' does not export a default function or 'render' function.`)
            }

            const pageOrProps = payload.page ?? payload.props ?? (payload.params as Record<string, unknown> | undefined) ?? {}
            const result = await renderFn(pageOrProps)

            const response: SsrRenderResponse = {
              id: payload.id,
              result: typeof result === "string" ? { body: result } : result,
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
