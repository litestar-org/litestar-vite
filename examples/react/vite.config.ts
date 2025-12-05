import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
    litestar({
      input: ["src/main.tsx"],
      resourceDirectory: "src",
    }),
  ],
})
