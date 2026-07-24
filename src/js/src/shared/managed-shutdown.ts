import type { ViteDevServer } from "vite"

const installedServers = new WeakSet<ViteDevServer>()

/**
 * Close a Python-managed Vite sidecar when its stdin pipe reaches EOF.
 *
 * @param server - Vite server owned by the Python parent process.
 * @param markShuttingDown - Optional callback for integration-specific shutdown state.
 */
export function installManagedShutdown(server: ViteDevServer, markShuttingDown?: () => void): void {
  if (process.env.LITESTAR_VITE_MANAGED !== "1" || installedServers.has(server)) {
    return
  }

  installedServers.add(server)
  let shuttingDown = false
  const shutdown = async (): Promise<void> => {
    if (shuttingDown) {
      return
    }
    shuttingDown = true
    markShuttingDown?.()
    try {
      await server.close()
    } finally {
      process.exit(0)
    }
  }

  process.stdin.on("end", shutdown)
  process.stdin.on("close", shutdown)
  process.stdin.resume()
}
