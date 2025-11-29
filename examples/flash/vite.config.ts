import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    litestar({
      input: ["resources/main.js"],
    }),
  ],
})
