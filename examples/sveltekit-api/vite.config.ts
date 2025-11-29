import { sveltekit } from "@sveltejs/kit/vite"
import tailwindcss from "@tailwindcss/vite"
import { litestarSvelteKit } from "litestar-vite-plugin/sveltekit"
import { defineConfig } from "vite"

const LITESTAR_PORT = process.env.LITESTAR_PORT || "8000"

export default defineConfig({
  plugins: [
    tailwindcss(),
    litestarSvelteKit({
      apiProxy: `http://localhost:${LITESTAR_PORT}`,
      apiPrefix: "/api",
    }),
    sveltekit(),
  ],
})
