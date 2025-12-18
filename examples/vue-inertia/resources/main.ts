import { createInertiaApp } from "@inertiajs/vue3"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import type { DefineComponent } from "vue"
import { createApp, h } from "vue"
import "./style.css"

// @ts-expect-error - useScriptElementForInitialPage is v2.3+ feature not yet in type definitions
createInertiaApp({
  // v2.3+ optimization: read page data from script element instead of data-page attribute
  useScriptElementForInitialPage: true,
  resolve: (name) => resolvePageComponent(`./pages/${name}.vue`, import.meta.glob<DefineComponent>("./pages/**/*.vue")),
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el)
  },
})
