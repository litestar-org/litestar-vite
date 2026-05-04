import { createInertiaApp } from "@inertiajs/react"
import { csrfHeaders } from "litestar-vite-plugin/helpers"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import type { ComponentType } from "react"
import { createRoot } from "react-dom/client"

import "./App.css"

const pages = import.meta.glob<{ default: ComponentType }>("./pages/**/*.tsx")

createInertiaApp({
  resolve: (name) => resolvePageComponent(`./pages/${name}.tsx`, pages),
  defaults: {
    visitOptions: (_href, options) => ({
      headers: csrfHeaders(options.headers ?? {}),
    }),
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />)
  },
})
