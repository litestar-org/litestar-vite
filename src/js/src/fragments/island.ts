export interface IslandOptions {
  component: string
  props: Record<string, unknown>
  islandId: string
}

function escapeHtmlAttr(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
}

export function wrapIsland(html: string, options: IslandOptions): string {
  const escapedProps = escapeHtmlAttr(JSON.stringify(options.props))
  const escapedComponent = escapeHtmlAttr(options.component)
  const escapedId = escapeHtmlAttr(options.islandId)
  return `<litestar-island data-island-component="${escapedComponent}" data-island-props="${escapedProps}" id="${escapedId}">${html}</litestar-island>`
}

export function getIslandClientScript(): string {
  return `<script type="module">
if (typeof window !== "undefined" && !customElements.get("litestar-island")) {
  customElements.define("litestar-island", class extends HTMLElement {
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
