import { resolve } from "node:path"
import litestarVitePlugin from "litestar-vite-plugin"
import { defineConfig } from "vite"

export default defineConfig({
  root: ".",
  base: "/",
  plugins: [
    litestarVitePlugin({
      input: [resolve(__dirname, "src/main.ts"), resolve(__dirname, "src/test.ts")],
    }),
  ],
  build: {
    manifest: true,
    outDir: resolve(__dirname, "../public"),
    emptyOutDir: true,
    rollupOptions: {
      input: [resolve(__dirname, "src/test.ts")],
      output: {
        entryFileNames: "assets/[name].[hash].js",
        chunkFileNames: "assets/[name].[hash].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },
  },
})
