import path from "node:path"
import { defineConfig } from "vitest/config"

export default defineConfig({
  resolve: {
    alias: {
      // Map package paths to source files for testing
      "litestar-vite-plugin/helpers": path.resolve(import.meta.dirname, "src/helpers/index.ts"),
      "litestar-vite-plugin/inertia-helpers": path.resolve(import.meta.dirname, "src/inertia-helpers/index.ts"),
      "litestar-vite-plugin/react": path.resolve(import.meta.dirname, "src/react/index.ts"),
      "litestar-vite-plugin/svelte": path.resolve(import.meta.dirname, "src/svelte/index.ts"),
      "litestar-vite-plugin/vue": path.resolve(import.meta.dirname, "src/vue/index.ts"),
      "litestar-vite-plugin": path.resolve(import.meta.dirname, "src/index.ts"),
    },
  },
  test: {
    globalSetup: ["./src/js/tests/global-setup.ts"],
    environment: "happy-dom",
    globals: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.d.ts", "src/**/types.ts", "**/__mocks__/**"],
      thresholds: {
        global: {
          lines: 80,
          functions: 80,
          branches: 80,
          statements: 80,
        },
      },
    },
  },
})
