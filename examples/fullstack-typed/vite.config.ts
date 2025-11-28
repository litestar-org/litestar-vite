import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "52283"
const LITESTAR_PORT = process.env.LITESTAR_PORT || "8000"

export default defineConfig({
  base: ASSET_URL,
  server: {
    host: "0.0.0.0",
    port: Number(VITE_PORT),
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    react(),
    litestar({
      input: ["resources/main.tsx"],
      assetUrl: ASSET_URL,
      bundleDirectory: "public",
      resourceDirectory: "resources",
    }),
  ],
  resolve: {
    alias: {
      "@": "/resources",
    },
  },
})
