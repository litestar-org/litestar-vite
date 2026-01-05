/**
 * Vite config for building the dev-server index page.
 *
 * This builds a self-contained HTML file with all CSS inlined,
 * which is then bundled into the npm package for distribution.
 *
 * Uses vite-plugin-singlefile to inline all assets into a single HTML file.
 */
import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"
import { viteSingleFile } from "vite-plugin-singlefile"

export default defineConfig({
  plugins: [tailwindcss(), viteSingleFile()],
  root: __dirname,
  build: {
    outDir: path.resolve(__dirname, "../../../../dist/js"),
    emptyDir: false,
    rollupOptions: {
      input: path.resolve(__dirname, "index.html"),
    },
    minify: true,
  },
})
