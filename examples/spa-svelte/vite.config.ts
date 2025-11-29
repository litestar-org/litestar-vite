import { svelte } from "@sveltejs/vite-plugin-svelte"
import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: Number(process.env.VITE_PORT || "43089"),
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    tailwindcss(),
    svelte(),
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
