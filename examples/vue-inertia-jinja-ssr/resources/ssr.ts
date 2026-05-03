import { createInertiaApp } from "@inertiajs/vue3"
import createServer from "@inertiajs/vue3/server"
import { renderToString } from "@vue/server-renderer"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import type { DefineComponent } from "vue"
import { createSSRApp, h } from "vue"

createServer(
  (page) =>
    createInertiaApp({
      page,
      render: renderToString,
      resolve: (name) => resolvePageComponent(`./pages/${name}.vue`, import.meta.glob<DefineComponent>("./pages/**/*.vue")),
      setup({ App, props, plugin }) {
        return createSSRApp({
          render: () => h(App, props),
        }).use(plugin)
      },
    }),
  Number.parseInt(process.env.INERTIA_SSR_PORT || "13714"),
)
