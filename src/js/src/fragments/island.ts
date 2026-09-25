export interface IslandOptions {
  component: string
  props: Record<string, unknown>
  islandId: string
}

export function wrapIsland(html: string, options: IslandOptions): string {
  const escapedProps = JSON.stringify(options.props).replace(/"/g, "&quot;")
  return `<vite-island data-island-component="${options.component}" data-island-props="${escapedProps}" id="${options.islandId}">${html}</vite-island>`
}

export function getIslandClientScript(): string {
  return `<script type="module">
if (typeof window !== "undefined" && !customElements.get("vite-island")) {
  customElements.define("vite-island", class extends HTMLElement {
    async connectedCallback() {
      const compPath = this.getAttribute("data-island-component")
      const rawProps = this.getAttribute("data-island-props")
      if (!compPath) return
      const props = rawProps ? JSON.parse(rawProps) : {}
      const mod = await import(/* @vite-ignore */ compPath)
      const Component = mod.default || mod
      if (typeof Component.hydrate === "function") {
        Component.hydrate({ target: this, props })
      }
    }
  })
}
</script>`
}
