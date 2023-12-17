import { defineConfig } from "vite";


import litestar from "litestar-vite-plugin";

const ASSET_URL =
  process.env.LITESTAR_ASSET_URL || process.env.ASSET_URL || "/static/";
const VITE_PORT = process.env.VITE_PORT || "5173";
const VITE_HOST = process.env.VITE_HOST || "localhost";
export default defineConfig({
  base: `${ASSET_URL}`,
   root: "web",
  server: {
    host: `${VITE_HOST}`,
    port: +`${VITE_PORT}`,
    cors: true,
  },
  plugins: [


    litestar({
      input: [
        "web/resources/styles.css", "web/resources/main.ts"
      ],
      assetUrl: `${ASSET_URL}`,
      bundleDirectory: "public",
      resourceDirectory: "resources",
      hotFile: "web/public/hot"
    }),
  ],
  resolve: {
    alias: {
      "@": "resources"
    },
  },
});
