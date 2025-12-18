import { createInertiaApp } from "@inertiajs/react"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./App.css"

// @ts-expect-error - useScriptElementForInitialPage is v2.3+ feature not yet in type definitions
createInertiaApp({
  // v2.3+ optimization: read page data from script element instead of data-page attribute
  useScriptElementForInitialPage: true,
  resolve: (name) => resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob("./pages/**/*.tsx")),
  setup({ el, App, props }) {
    createRoot(el).render(
      <StrictMode>
        <App {...props} />
      </StrictMode>,
    )
  },
})
