import angular from "@analogjs/vite-plugin-angular"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: process.env.VITE_HOST || "127.0.0.1",
    port: Number(process.env.VITE_PORT || "46053"),
    cors: true,
    hmr: {
      host: "localhost",
      path: "/vite-hmr",
    },
  },
  plugins: [
    angular(),
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
