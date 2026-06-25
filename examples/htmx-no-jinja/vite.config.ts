import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"
export default defineConfig({
  plugins: [
    litestar({
      input: ["resources/main.js"],
    }),
  ],
  build: {
    rolldownOptions: {
      onwarn(warning, warn) {
        // Suppress eval warnings from htmx (htmx uses eval for dynamic attribute evaluation)
        if (warning.code === "EVAL" && warning.id?.includes("htmx")) {
          return
        }
        warn(warning)
      },
    },
  },
})
