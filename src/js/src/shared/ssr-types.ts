export interface SsrRenderRequest {
  id?: number | string
  type?: "inertia" | "fragment"
  entrypoint?: string
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
    body: string
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
  endpoint?: string
  hmr?: boolean
  stdioIpc?: boolean
}
