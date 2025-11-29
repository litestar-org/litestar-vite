import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "44477"),
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    litestar({
      input: ["resources/main.js"],
    }),
  ],
  resolve: {
    alias: {
      "@": "/resources",
    },
  },
})
