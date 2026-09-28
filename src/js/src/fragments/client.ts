export type IslandTeardown = () => void | Promise<void>
export type IslandHydrator = (component: any, target: HTMLElement, props: Record<string, unknown>) => IslandTeardown | Promise<IslandTeardown>
export interface IslandComponent {
  load: () => Promise<{ default: any }>
  hydrate: IslandHydrator
}

/** Register compiled component imports and hydrate present and subsequently inserted islands. */
export function hydrateIslands(registry: Record<string, IslandComponent>): void {
  if (customElements.get("litestar-island")) return
  customElements.define(
    "litestar-island",
    class extends HTMLElement {
      private revision = 0
      private work: Promise<void> = Promise.resolve()
      private teardown?: IslandTeardown
      private serverMarkup?: string

      connectedCallback(): void {
        this.schedule()
      }

      disconnectedCallback(): void {
        this.schedule()
      }

      private schedule(): void {
        const revision = ++this.revision
        // Serialize loading, hydration and teardown so reconnecting cannot create overlapping roots.
        this.work = this.work
          .then(() => this.reconcile(revision))
          .catch((error: unknown) => {
            this.dispatchEvent(new CustomEvent("litestar:island-error", { detail: error, bubbles: true }))
            console.error("Failed to update Litestar island", error)
          })
      }

      private async destroy(teardown = this.teardown): Promise<void> {
        this.teardown = undefined
        if (!teardown) return
        try {
          await teardown()
        } finally {
          // Framework unmounting removes DOM. Preserve SSR markup for a later reconnection.
          this.innerHTML = this.serverMarkup ?? ""
        }
      }

      private async reconcile(revision: number): Promise<void> {
        if (revision !== this.revision) return
        if (!this.isConnected) {
          await this.destroy()
          return
        }
        if (this.teardown) return
        const id = this.getAttribute("data-island-component") || ""
        if (!Object.hasOwn(registry, id)) throw new Error(`Unknown island component: ${id}`)
        const definition = registry[id]
        const props = JSON.parse(this.getAttribute("data-island-props") || "{}")
        const component = await definition.load()
        if (revision !== this.revision || !this.isConnected) return
        this.serverMarkup ??= this.innerHTML
        const teardown = await definition.hydrate(component.default, this, props)
        if (revision !== this.revision || !this.isConnected) {
          await this.destroy(teardown)
          return
        }
        this.teardown = teardown
        this.dispatchEvent(new CustomEvent("litestar:island-ready", { bubbles: true }))
      }
    },
  )
}
