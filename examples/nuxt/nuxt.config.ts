import tailwindcss from "@tailwindcss/vite"

// Litestar manages the dev server port via VITE_PORT and runtime config.
// The Nuxt module reads the port automatically - no hardcoding needed.
// LITESTAR_PORT is the backend API server port (default 8000).
const LITESTAR_PORT = process.env.LITESTAR_PORT ?? "8000"

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },
  modules: ["litestar-vite-plugin/nuxt"],

  vite: {
    plugins: [tailwindcss()],
  },

  litestar: {
    // API proxy points to the Litestar backend (apiPrefix defaults to "/api")
    apiProxy: `http://127.0.0.1:${LITESTAR_PORT}`,
    verbose: true,
    // Match Python TypeGenConfig paths (defaults are "types/api", "openapi.json", "routes.json")
    types: {
      output: "generated",
      openapiPath: "generated/openapi.json",
      routesPath: "generated/routes.json",
    },
  },
})
