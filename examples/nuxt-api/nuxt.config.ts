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
    // API proxy points to the Litestar backend, not the Nuxt dev server
    apiProxy: `http://localhost:${LITESTAR_PORT}`,
    apiPrefix: "/api",
  },
})
