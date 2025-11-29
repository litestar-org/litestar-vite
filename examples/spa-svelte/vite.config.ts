import { svelte } from "@sveltejs/vite-plugin-svelte"
import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte(),
    litestar({
      input: ["src/main.ts"],
    }),
  ],
})
