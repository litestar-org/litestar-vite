import { createInertiaApp } from "@inertiajs/react"
import { csrfHeaders } from "litestar-vite-plugin/helpers"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import { createRoot } from "react-dom/client"
import "./App.css"

createInertiaApp({
  resolve: async (name) => (await resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob("./pages/**/*.tsx"))).default,
  defaults: {
    visitOptions: (_href, options) => ({
      headers: csrfHeaders(options.headers ?? {}),
    }),
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />)
  },
})
