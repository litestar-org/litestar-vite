import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    vue(),
    litestar({
      input: ["resources/main.ts"],
    }),
  ],
})
