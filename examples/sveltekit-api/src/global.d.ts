type ServerRoutes = typeof import("./lib/generated/routes.json")["routes"]

declare global {
  interface Window {
    serverRoutes?: ServerRoutes
    __LITESTAR_ROUTES__?: ServerRoutes
  }
}

export {}
