import { defineConfig } from "vite";

import litestar from "litestar-vite-plugin";

const ASSET_URL = process.env.ASSET_URL || "/static/";
const VITE_PORT = process.env.VITE_PORT || "5173";
const VITE_HOST = process.env.VITE_HOST || "localhost";
export default defineConfig({
  base: `${ASSET_URL}`,
  server: {
    host: `${VITE_HOST}`,
    port: +`${VITE_PORT}`,
    cors: true,
  },
  plugins: [
    litestar({
      input: ["resources/styles.css", "resources/main.ts"],
      assetUrl: `${ASSET_URL}`,
    }),
  ],
  resolve: {
    alias: {
      "@": "resources",
    },
  },
});
