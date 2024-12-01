import { defineConfig } from "vite"

import litestar from "litestar-vite-plugin"

const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "5173"
const VITE_HOST = process.env.VITE_HOST || "localhost"
export default defineConfig({
  base: `${ASSET_URL}`,
  root: ".",
  server: {
    host: "0.0.0.0",
    port: +`${VITE_PORT}`,
    cors: true,
    hmr: {
      host: `${VITE_HOST}`,
    },
  },
  plugins: [
    litestar({
      input: ["resources/main.ts", "resources/styles.css"],
      assetUrl: `${ASSET_URL}`,
      bundleDirectory: "public",
      resourceDirectory: "resources",
      hotFile: "public/hot",
    }),
  ],
  resolve: {
    alias: {
      "@": "resources",
    },
  },
})
