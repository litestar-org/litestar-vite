import { defineConfig } from "vite";

import litestar from "litestar-vite-plugin";

export default defineConfig({
  root: "web",
  plugins: [
    litestar({
      input: ["resources/assets/main.ts", "resources/assets/styles.css"],
      assetUrl: "/static/",
      assetDirectory: "resources/assets",
      bundleDirectory: "public",
      resourceDirectory: "resources",
    }),
  ],
  resolve: {
    alias: {
      "@": "resources",
    },
  },
});
