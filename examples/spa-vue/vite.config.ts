import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "53255"),
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    tailwindcss(),
    vue(),
    litestar({
      input: ["src/main.ts"],
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
})
