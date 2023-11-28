import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

import litestar from "litestar-vite-plugin";

export default defineConfig({
  plugins: [
    vue(),
    
    litestar({
      input: [
        "resources/styles.css"
      ],
      assetUrl: "/static/",
      assetDirectory: "resources/assets",
      bundleDirectory: "public",
      resourceDirectory: "resources"
    }),
  ],
  resolve: {
    alias: {
      "@": "resources"
    },
  },
});