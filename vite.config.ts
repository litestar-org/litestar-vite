import { defineConfig } from "vite";

import litestar from "litestar-vite-plugin";

const ASSET_URL = process.env.ASSET_URL || "/static/";
const VITE_PORT = process.env.VITE_PORT || "5173";
const VITE_HOST = process.env.VITE_HOST || "localhost";
export default defineConfig({
  base: `${ASSET_URL}`,
  root: "examples/vanilla",
  server: {
    host: `${VITE_HOST}`,
    port: +`${VITE_PORT}`,
    cors: true,
  },
  plugins: [
    litestar({
      input: [
        "examples/vanilla/resources/styles.css",
        "examples/vanilla/resources/main.ts",
      ],
      assetUrl: `${ASSET_URL}`,
      bundleDirectory: "public",
      resourceDirectory: "resources",
      hotFile: "examples/vanilla/public/hot",
    }),
  ],
  resolve: {
    alias: {
      "@": "resources",
    },
  },
});
