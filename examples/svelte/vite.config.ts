import { svelte } from "@sveltejs/vite-plugin-svelte"
import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import type { PluginOption } from "vite"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte(),
    ...(litestar({
      input: ["src/main.ts"],
    }) as PluginOption[]),
  ],
})
