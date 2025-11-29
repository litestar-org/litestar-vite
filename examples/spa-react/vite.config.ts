import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { type PluginOption, defineConfig } from "vite"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "38533"

export default defineConfig({
  base: ASSET_URL,
  server: {
    host: "0.0.0.0",
    port: Number(VITE_PORT),
    cors: true,
  },
  plugins: [
    tailwindcss(),
    react(),
    ...(litestar({
      input: ["src/main.tsx"],
      assetUrl: ASSET_URL,
      bundleDirectory: "public",
      resourceDirectory: "src",
      types: {
        enabled: true,
        openapiPath: "src/generated/openapi.json",
        routesPath: "src/generated/routes.json",
        output: "src/generated",
        generateZod: true,
        generateSdk: true,
      },
    }) as PluginOption[]),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
})
