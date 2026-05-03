import { createInertiaApp } from "@inertiajs/svelte"
import { csrfHeaders } from "litestar-vite-plugin/helpers"
import { mount, type Component } from "svelte"
import "./app.css"

const pages = import.meta.glob<{ default: Component }>("./pages/**/*.svelte")

createInertiaApp({
  resolve: async (name) => {
    const path = `./pages/${name}.svelte`
    const page = pages[path]
    if (!page) throw new Error(`Page not found: ${path}`)
    return page()
  },
  defaults: {
    visitOptions: (_href, options) => ({
      headers: csrfHeaders(options.headers ?? {}),
    }),
  },
  setup({ el, App, props }) {
    mount(App, {
      target: el,
      props,
    })
  },
})
