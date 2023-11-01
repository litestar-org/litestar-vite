import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import litestar from "litestar-vite-plugin";

function getBackendUrl(path: string) {
  return `${process.env.FRONTEND_URL || "http://localhost:8000"}${path}`;
}
const STATIC_URL = process.env.STATIC_URL || "/static/";
export default defineConfig({
  base: `${STATIC_URL}`,
  plugins: [
    vue(),
    litestar({
      input: ["src/app/domain/web/resources/main.ts"],
      assetUrl: "/static/",
      assetDirectory: "False"
      bundleDirectory: "False",
      resourceDirectory: "False"
    }),
  ],
  resolve: {
    alias: {
      "@": "False",
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3006,
    cors: true,
    strictPort: true,
    watch: {
      ignored: ["node_modules", ".venv", "**/__pycache__/**"],
    },
  },
});