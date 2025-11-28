import angular from "@analogjs/vite-plugin-angular"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = Number(process.env.VITE_PORT || "46053")
const VITE_HOST = process.env.VITE_HOST || "127.0.0.1"
const LITESTAR_PORT = Number(process.env.LITESTAR_PORT || "8000")

export default defineConfig({
  base: ASSET_URL,
  server: {
    host: VITE_HOST,
    port: VITE_PORT,
    cors: true,
    hmr: {
      host: "localhost",
      path: "/vite-hmr",
    },
  },
  plugins: [
    angular(),
    litestar({
      input: ["src/main.ts"],
      assetUrl: ASSET_URL,
      bundleDirectory: "public",
      resourceDirectory: "src",
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
})
