import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import litestar from "@litestar/vite-plugin";
import { resolve } from "path";

export default defineConfig({
  plugins: [
    vue(),
    litestar({
      input: ["src/main.ts"],
      assetUrl: "/static/",
      bundleDir: "public",
      resourceDir: "src",
    }),
  ],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
});
