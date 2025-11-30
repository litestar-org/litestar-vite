declare global {
  interface Window {
    serverRoutes?: Record<string, unknown>
    __LITESTAR_ROUTES__?: Record<string, unknown>
  }
}
export {}
