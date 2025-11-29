import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "52283"),
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
