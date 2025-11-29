import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    litestar({
      input: ["resources/main.js"],
    }),
  ],
})
