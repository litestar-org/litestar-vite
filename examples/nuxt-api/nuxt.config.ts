import tailwindcss from "@tailwindcss/vite"

const LITESTAR_PORT = process.env.LITESTAR_PORT || "8000"

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },
  modules: ["litestar-vite-plugin/nuxt"],

  vite: {
    plugins: [tailwindcss()],
  },

  litestar: {
    apiProxy: `http://localhost:${LITESTAR_PORT}`,
    apiPrefix: "/api",
  },
})
