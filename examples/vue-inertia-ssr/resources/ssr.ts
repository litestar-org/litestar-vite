import { createInertiaApp } from "@inertiajs/vue3"
import { renderToString } from "@vue/server-renderer"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import { startSsrWorker } from "litestar-vite-plugin/ssr-worker"
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
  startSsrWorker({ render })
}
