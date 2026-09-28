import { createElement } from "react"
import { hydrateRoot } from "react-dom/client"
import type { IslandHydrator } from "./client.js"

export const hydrateReact: IslandHydrator = (component, target, props) => {
  const root = hydrateRoot(target, createElement(component, props))
  return () => root.unmount()
}
