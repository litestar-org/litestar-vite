import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "astro/config"
import litestar from "litestar-vite-plugin/astro"

const LITESTAR_PORT = process.env.LITESTAR_PORT || "8000"

export default defineConfig({
  integrations: [
    litestar({
      apiProxy: `http://localhost:${LITESTAR_PORT}`,
      apiPrefix: "/api",
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
})
