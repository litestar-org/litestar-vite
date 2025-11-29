import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { type PluginOption, defineConfig } from "vite"

export default defineConfig({
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
})
