import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "5173"),
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
    }),
  ],
  resolve: {
    alias: {
      "@": "/resources",
    },
  },
})
