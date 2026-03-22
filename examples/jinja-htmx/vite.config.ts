import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig, version } from "vite"

const bundlerKey = Number(version.split(".")[0]) >= 8 ? "rolldownOptions" : "rollupOptions"

export default defineConfig({
  plugins: [
    tailwindcss(),
    litestar({
      input: ["resources/main.js"],
    }),
  ],
  build: {
    [bundlerKey]: {
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
