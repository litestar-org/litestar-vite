export interface SsrRenderRequest {
  id?: number | string
  method?: string
  type?: "inertia" | "fragment"
  mode?: "static" | "island"
  params?: Record<string, unknown>
  page?: {
    component: string
    props: Record<string, unknown>
    url: string
    version?: string
  }
  component?: string
  props?: Record<string, unknown>
}

export interface SsrRenderResponse {
  id?: number | string
  result?: {
    head?: string[]
    body?: string
    html?: string
    css?: string[]
    [key: string]: unknown
  }
  error?: {
    message: string
    stack?: string
    name?: string
  }
}

export interface DevSsrOptions {
  entrypoint?: string
  /** Directories containing renderable components, relative to the Vite root. */
  componentRoots?: string[]
  /** Browser entry module registering island components and framework adapters. */
  clientEntry?: string
  endpoint?: string
  hmr?: boolean
}
