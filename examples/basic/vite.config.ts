import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "59279"
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
    litestar({
      input: ["resources/main.js"],
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
