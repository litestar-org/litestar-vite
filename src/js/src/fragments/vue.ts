import { createSSRApp } from "vue"
import type { IslandHydrator } from "./client.js"

export const hydrateVue: IslandHydrator = (component, target, props) => {
  const app = createSSRApp(component, props)
  app.mount(target)
  return () => app.unmount()
}
