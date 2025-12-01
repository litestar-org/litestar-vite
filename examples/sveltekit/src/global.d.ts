type ServerRoutes = typeof import("./lib/generated/routes.json")["routes"]

// CSS module declarations for TypeScript
declare module "*.css" {
  const content: Record<string, string>
  export default content
}

declare global {
  interface Window {
    serverRoutes?: ServerRoutes
    __LITESTAR_ROUTES__?: ServerRoutes
  }
}

export {}
