import { defineConfig } from "astro/config"
import litestar from "litestar-vite-plugin/astro"

import tailwindcss from "@tailwindcss/vite"

const LITESTAR_PORT = process.env.LITESTAR_PORT || "8000"

export default defineConfig({
  integrations: [
    litestar({
      apiProxy: `http://localhost:${LITESTAR_PORT}`,
      apiPrefix: "/api",

      typesPath: "./src/generated/api",
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
})
