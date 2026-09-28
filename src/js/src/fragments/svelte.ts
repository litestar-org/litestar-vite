import { hydrate, unmount } from "svelte"
import type { IslandHydrator } from "./client.js"

export const hydrateSvelte: IslandHydrator = (component, target, props) => {
  const instance = hydrate(component, { target, props })
  return () => unmount(instance)
}
