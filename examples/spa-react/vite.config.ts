import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { type PluginOption, defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "38533"),
    cors: true,
  },
  plugins: [
    tailwindcss(),
    react(),
    ...(litestar({
      input: ["src/main.tsx"],
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
