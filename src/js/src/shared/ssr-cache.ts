import type { ViteDevServer } from "vite"
import type { ModuleRunner } from "vite/module-runner"

export function manageSsrCache(runner: ModuleRunner, server: ViteDevServer) {
  function invalidateNodeAndImporters(id: string, visited = new Set<string>()): void {
    if (visited.has(id)) return
    visited.add(id)
    const node = runner.evaluatedModules.getModuleById(id)
    if (!node) return
    runner.evaluatedModules.invalidateModule(node)
    for (const importerId of node.importers) {
      invalidateNodeAndImporters(importerId, visited)
    }
  }

  function onFileChange(file: string): void {
    // Normalize Windows backslashes to POSIX forward slashes
    const normalized = file.replace(/\\/g, "/")
    const nodes = runner.evaluatedModules.getModulesByFile(normalized)
    if (!nodes || nodes.size === 0) return
    for (const node of nodes) {
      invalidateNodeAndImporters(node.id)
    }
  }

  server.watcher.on("change", onFileChange)
  server.watcher.on("unlink", onFileChange)

  return {
    clearAll() {
      runner.evaluatedModules.clear()
    },
    dispose() {
      server.watcher.off("change", onFileChange)
      server.watcher.off("unlink", onFileChange)
    },
  }
}
