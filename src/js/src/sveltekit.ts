/**
 * SvelteKit integration for Litestar-Vite.
 *
 * This module provides a Vite plugin specifically designed to work alongside
 * SvelteKit's own Vite plugin. It enables:
 * - API proxy configuration for dev server
 * - Type generation integration (shares @hey-api/openapi-ts output)
 * - Seamless integration with SvelteKit's load functions
 *
 * @example
 * ```typescript
 * // vite.config.ts
 * import { sveltekit } from '@sveltejs/kit/vite';
 * import { litestarSvelteKit } from 'litestar-vite-plugin/sveltekit';
 * import { defineConfig } from 'vite';
 *
 * export default defineConfig({
 *   plugins: [
 *     litestarSvelteKit({
 *       apiProxy: 'http://localhost:8000',
 *       types: true,
 *     }),
 *     sveltekit(),  // SvelteKit plugin comes after
 *   ],
 * });
 * ```
 *
 * @module
 */

import fs from "node:fs"
import type { IncomingMessage, ServerResponse } from "node:http"
import path from "node:path"
import colors from "picocolors"
import type { ViteDevServer } from "vite"
import { type LitestarIntegrationConfig, resolveIntegrationConfig, type ResolvedIntegrationConfig } from "./shared/integration-config.js"
import { installManagedShutdown } from "./shared/managed-shutdown.js"
import { normalizeHost } from "./shared/network.js"
import { createLitestarTypeGenPlugin, type TypesConfigShape } from "./shared/typegen-plugin.js"
import { hmrServerConfig } from "./shared/vite-compat.js"

/**
 * Configuration for TypeScript type generation.
 *
 * Alias of the shared {@link TypesConfigShape} so every integration accepts an identical
 * `types` option. Retained as a named export for backwards compatibility.
 */
export type SvelteKitTypesConfig = TypesConfigShape

/**
 * Configuration options for the Litestar integration.
 *
 * Alias of the shared {@link LitestarIntegrationConfig}. Retained as a named export for
 * backwards compatibility.
 */
export type LitestarSvelteKitConfig = LitestarIntegrationConfig

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarSvelteKitConfig = {}): ResolvedIntegrationConfig {
  return resolveIntegrationConfig(config, "src/lib/generated")
}

/**
 * Litestar integration plugin for SvelteKit.
 *
 * This plugin should be added BEFORE the sveltekit() plugin in your vite.config.ts.
 * It provides API proxying during development and integrates type generation.
 *
 * @param userConfig - Configuration options for the integration
 * @returns A Vite plugin array
 *
 * @example
 * ```typescript
 * // vite.config.ts
 * import { sveltekit } from '@sveltejs/kit/vite';
 * import { litestarSvelteKit } from 'litestar-vite-plugin/sveltekit';
 * import { defineConfig } from 'vite';
 *
 * export default defineConfig({
 *   plugins: [
 *     litestarSvelteKit({
 *       apiProxy: 'http://localhost:8000',
 *       apiPrefix: '/api',
 *       types: {
 *         enabled: true,
 *         output: 'src/lib/generated',
 *         generateZod: true,
 *       },
 *     }),
 *     sveltekit(),
 *   ],
 * });
 * ```
 *
 * @example Using with SvelteKit load functions
 * ```typescript
 * // src/routes/users/[id]/+page.ts
 * import type { PageLoad } from './$types';
 * import type { User } from '$lib/generated/api/types.gen';
 * import { route } from '$lib/generated/routes';
 *
 * export const load: PageLoad = async ({ params, fetch }) => {
 *   const response = await fetch(route('users.show', { id: params.id }));
 *   const user: User = await response.json();
 *   return { user };
 * };
 * ```
 */
export function litestarSvelteKit(userConfig: LitestarSvelteKitConfig = {}): any[] {
  const config = resolveConfig(userConfig)
  // Avoid leaking Vite's private plugin types across linked workspaces.
  // The runtime shape is still a normal Vite plugin array.
  const plugins: any[] = []

  // Main plugin for proxy and logging
  plugins.push({
    name: "litestar-sveltekit",
    enforce: "pre",

    config() {
      const hmrPath = `${(config.assetUrl ?? "/static").replace(/\/$/, "")}/vite-hmr`
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, SvelteKit might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
          // Set the port from Python config/env to ensure SvelteKit uses the expected port
          // strictPort: true prevents SvelteKit from auto-incrementing to a different port
          ...(config.port !== undefined
            ? {
                port: config.port,
                strictPort: true,
              }
            : {}),
          // Route HMR through the Litestar port so DevTools never sees the framework port.
          ...(config.litestarPort !== undefined
            ? hmrServerConfig({
                protocol: "ws" as const,
                host: "127.0.0.1",
                clientPort: config.litestarPort,
                path: hmrPath,
              })
            : {}),
          proxy: {
            [config.apiPrefix]: {
              target: config.apiProxy,
              changeOrigin: true,
              secure: false,
              ws: true,
            },
          },
        },
      }
    },

    configureServer(server: ViteDevServer) {
      installManagedShutdown(server)
      if (config.verbose) {
        server.middlewares.use((req: IncomingMessage, _res: ServerResponse, next: () => void) => {
          if (req.url?.startsWith(config.apiPrefix)) {
            console.log(colors.cyan("[litestar-sveltekit]"), `Proxying: ${req.method} ${req.url}`)
          }
          next()
        })
      }

      // Always write hotfile - proxy mode needs it for dynamic target discovery
      if (config.hotFile) {
        const hotFile = config.hotFile

        server.httpServer?.once("listening", () => {
          const address = server.httpServer?.address()
          if (address && typeof address === "object" && "port" in address) {
            const host = normalizeHost(address.address)
            const url = `http://${host}:${address.port}`
            fs.mkdirSync(path.dirname(hotFile), { recursive: true })
            fs.writeFileSync(hotFile, url)
            if (config.verbose) {
              console.log(colors.cyan("[litestar-sveltekit]"), colors.dim(`Hotfile written: ${hotFile} -> ${url}`))
            }
          }
        })
      }

      // Log startup info
      server.httpServer?.once("listening", () => {
        setTimeout(() => {
          console.log("")
          console.log(`  ${colors.cyan("[litestar-sveltekit]")} ${colors.green("Integration active")}`)
          console.log(`  ${colors.dim("├─")} API Proxy: ${colors.yellow(config.apiProxy)}`)
          console.log(`  ${colors.dim("├─")} API Prefix: ${colors.yellow(config.apiPrefix)}`)
          if (config.types !== false && config.types.enabled) {
            console.log(`  ${colors.dim("└─")} Types Output: ${colors.yellow(config.types.output)}`)
          } else {
            console.log(`  ${colors.dim("└─")} Types: ${colors.dim("disabled")}`)
          }
          console.log("")
        }, 100)
      })
    },
  })

  // Type generation plugin (if enabled)
  if (config.types !== false && config.types.enabled) {
    plugins.push(
      createLitestarTypeGenPlugin(config.types, {
        pluginName: "litestar-sveltekit-types",
        frameworkName: "litestar-sveltekit",
        sdkClientPlugin: "@hey-api/client-fetch",
        executor: config.executor,
        hasPythonConfig: config.hasPythonConfig,
      }),
    )
  }

  return plugins
}

// Default export for simpler imports
export default litestarSvelteKit
