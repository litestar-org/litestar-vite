import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { TanStackRouterVite } from "@tanstack/router-plugin/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "5005"),
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    tailwindcss(),
    TanStackRouterVite(),
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
