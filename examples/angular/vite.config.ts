import angular from "@analogjs/vite-plugin-angular"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    angular(),
    litestar({
      input: ["src/main.ts"],
    }),
  ],
})
