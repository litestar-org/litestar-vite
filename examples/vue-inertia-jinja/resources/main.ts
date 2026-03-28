import { createInertiaApp } from "@inertiajs/vue3"
import { csrfHeaders } from "litestar-vite-plugin/helpers"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import type { DefineComponent } from "vue"
import { createApp, h } from "vue"
import "./style.css"

createInertiaApp({
  resolve: (name) => resolvePageComponent(`./pages/${name}.vue`, import.meta.glob<DefineComponent>("./pages/**/*.vue")),
  defaults: {
    visitOptions: (_href, options) => ({
      headers: csrfHeaders(options.headers ?? {}),
    }),
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el)
  },
})
