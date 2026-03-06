import { sveltekit } from "@sveltejs/kit/vite"
import tailwindcss from "@tailwindcss/vite"
import { litestarSvelteKit } from "litestar-vite-plugin/sveltekit"
import { defineConfig, type PluginOption } from "vite"

// Litestar manages the dev server port via VITE_PORT and runtime config.
// The SvelteKit plugin reads the port automatically - no hardcoding needed.
// LITESTAR_PORT is the backend API server port (default 8000).
const LITESTAR_PORT = process.env.LITESTAR_PORT ?? "8000"
const litestarPlugins = litestarSvelteKit({
  apiProxy: `http://localhost:${LITESTAR_PORT}`,
  apiPrefix: "/api",
}) as PluginOption[]

export default defineConfig({
  plugins: [
    tailwindcss(),
    ...litestarPlugins,
    sveltekit(),
  ],
})
