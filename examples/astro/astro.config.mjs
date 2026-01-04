import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "astro/config"
import litestar from "litestar-vite-plugin/astro"

// Litestar manages the dev server port via VITE_PORT and runtime config.
// The Astro integration reads the port automatically - no hardcoding needed.
// LITESTAR_PORT is the backend API server port (default 8000).
const LITESTAR_PORT = process.env.LITESTAR_PORT ?? "8000"

export default defineConfig({
  integrations: [
    litestar({
      // API proxy points to the Litestar backend
      apiProxy: `http://localhost:${LITESTAR_PORT}`,
      apiPrefix: "/api",
      types: true,
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
})
