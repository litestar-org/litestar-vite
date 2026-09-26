import path from "node:path"
import { wrapIsland } from "./island.js"

export interface RenderFragmentOptions {
  componentPath: string
  props?: Record<string, unknown>
  mode?: "static" | "island"
  islandId?: string
}

export interface RenderFragmentResult {
  html: string
  head: string[]
  css: string[]
}

function dynamicImport(specifier: string): Promise<any> {
  return import(/* @vite-ignore */ specifier)
}

export async function renderFragment(options: RenderFragmentOptions, customImporter?: (specifier: string) => Promise<any>): Promise<RenderFragmentResult> {
  const { componentPath, props = {}, mode = "static", islandId } = options
  const importer = customImporter || ((spec: string) => dynamicImport(spec))
  const ext = path.extname(componentPath).toLowerCase()

  const module = await importer(componentPath)
  const Component = module.default || module

  let renderedHtml = ""
  const head: string[] = []
  const css: string[] = []

  if (ext === ".tsx" || ext === ".jsx") {
    const React = await dynamicImport("react")
    const ReactDOMServer = await dynamicImport("react-dom/server")
    if (mode === "static" && typeof ReactDOMServer.renderToStaticMarkup === "function") {
      renderedHtml = ReactDOMServer.renderToStaticMarkup(React.createElement(Component, props))
    } else {
      renderedHtml = ReactDOMServer.renderToString(React.createElement(Component, props))
    }
  } else if (ext === ".vue") {
    const { createSSRApp } = await dynamicImport("vue")
    const { renderToString } = await dynamicImport("vue/server-renderer")
    const app = createSSRApp(Component, props)
    renderedHtml = await renderToString(app)
  } else if (ext === ".svelte") {
    const svelteServer = await dynamicImport("svelte/server")
    const result = svelteServer.render(Component, { props })
    renderedHtml = result.html
    if (result.head) head.push(result.head)
  } else if (ext === ".astro") {
    const { experimental_AstroContainer } = await dynamicImport("astro/container")
    const container = await experimental_AstroContainer.create()
    renderedHtml = await container.renderToString(Component, { props })
  } else {
    throw new Error(`Unsupported component extension for fragment rendering: ${ext}`)
  }

  if (mode === "island") {
    const effectiveIslandId = islandId || `island-${Math.random().toString(36).slice(2, 10)}`
    renderedHtml = wrapIsland(renderedHtml, {
      component: componentPath,
      props,
      islandId: effectiveIslandId,
    })
  }

  return { html: renderedHtml, head, css }
}
