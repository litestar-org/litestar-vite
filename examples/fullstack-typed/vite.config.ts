import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

import tailwindcss from "@tailwindcss/vite"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "5173"
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
    tailwindcss(),

    react(),
    litestar({
      input: ["resources/main.tsx"],
      assetUrl: ASSET_URL,
      bundleDirectory: "public",
      resourceDirectory: "resources",

      types: {
        enabled: true,
        schemaPath: "./openapi.json",
        routesPath: "./routes.json",
        output: "resources/generated/api",
      },
    }),
  ],
  resolve: {
    alias: {
      "@": "/resources",
    },
  },
})
