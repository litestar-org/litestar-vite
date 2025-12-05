import angular from "@analogjs/vite-plugin-angular"
import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  resolve: {
    mainFields: ["module"],
  },
  plugins: [
    // Angular plugin must be first
    angular(),
    tailwindcss(),
    litestar({
      input: ["src/main.ts", "src/styles.css"],
      resourceDirectory: "src",
    }),
  ],
})
