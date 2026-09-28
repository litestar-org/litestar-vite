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

export function getIslandClientScript(clientEntry: string): string {
  if (!/^(?:\/(?!\/)|https?:\/\/)/.test(clientEntry)) {
    throw new Error("Island clientEntry must be a root-relative or HTTP(S) URL to a built client registry")
  }
  return `<script type="module" src="${escapeHtmlAttr(clientEntry)}"></script>`
}
