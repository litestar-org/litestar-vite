import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "5005"),
    cors: true,
    ws: {
      host: "localhost",
    },
  },
  plugins: [
    tailwindcss(),
    tanstackRouter({
      target: "react",
      routesDirectory: "src/routes",
      generatedRouteTree: "src/generated/routeTree.gen.ts",
    }),
    react(),
    litestar({
      input: ["src/main.tsx"],
      types: "auto",
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
})
