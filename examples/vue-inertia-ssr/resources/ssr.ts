import readline from "node:readline"
import { createInertiaApp } from "@inertiajs/vue3"
import { renderToString } from "@vue/server-renderer"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import type { DefineComponent } from "vue"
import { createSSRApp, h } from "vue"

const pages = import.meta.glob<DefineComponent>("./pages/**/*.vue")

export default async function render(page: any): Promise<any> {
  return createInertiaApp({
    page,
    render: renderToString,
    resolve: (name) => resolvePageComponent(`./pages/${name}.vue`, pages),
    setup({ App, props, plugin }) {
      return createSSRApp({
        render: () => h(App, props),
      }).use(plugin)
    },
  })
}

if (!import.meta.env?.DEV) {
  const rl = readline.createInterface({
    input: process.stdin,
    terminal: false,
    crlfDelay: Number.POSITIVE_INFINITY,
  })

  rl.on("line", async (line) => {
    const trimmed = line.trim()
    if (!trimmed) return
    let requestId: number | string | null = null
    try {
      const request = JSON.parse(trimmed)
      requestId = request.id ?? null
      const page = request.params?.page ?? request.params ?? request.payload ?? request
      const result = await render(page)
      process.stdout.write(`${JSON.stringify({ id: requestId, result })}\n`)
    } catch (error: any) {
      process.stdout.write(`${JSON.stringify({ id: requestId, error: error?.message || String(error) })}\n`)
    }
  })

  rl.on("close", () => process.exit(0))
  process.stdin.on("end", () => process.exit(0))
}
