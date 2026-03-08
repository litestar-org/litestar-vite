import tailwindcss from "@tailwindcss/vite"

// Litestar manages the dev server port via VITE_PORT and runtime config.
// The Nuxt module reads the port automatically - no hardcoding needed.
// LITESTAR_PORT is the backend API server port (default 8000).
const LITESTAR_PORT = process.env.LITESTAR_PORT ?? "8000"

export default defineNuxtConfig({
  compatibilityDate: "2026-03-06",
  devtools: { enabled: true },
  modules: ["litestar-vite-plugin/nuxt"],
  css: ["~/assets/css/app.css"],
  vite: {
    plugins: [tailwindcss()],
  },
  litestar: {
    // API proxy points to the Litestar backend (apiPrefix defaults to "/api").
    apiProxy: `http://127.0.0.1:${LITESTAR_PORT}`,
    types: true,
  },
})
