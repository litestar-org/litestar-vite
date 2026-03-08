import { createInertiaApp } from "@inertiajs/react"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import { createRoot } from "react-dom/client"
import "./App.css"

createInertiaApp({
  defaults: {
    future: {
      useScriptElementForInitialPage: true,
    },
  },
  resolve: (name) => resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob("./pages/**/*.tsx")),
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />)
  },
})
