import type { Logger, ResolvedConfig } from "vite"
import { vi } from "vitest"

/**
 * Creates a mock Vite resolved configuration for testing.
 */
export function createMockViteConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
  const mockLogger: Logger = {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    warnOnce: vi.fn(),
    clearScreen: vi.fn(),
    hasWarned: false,
    hasErrorLogged: vi.fn(() => false),
  }

  return {
    root: "/test/root",
    base: "/",
    mode: "development",
    command: "serve",
    envDir: process.cwd(),
    envPrefix: "VITE_",
    resolve: {
      alias: [],
      dedupe: [],
      conditions: [],
      mainFields: ["browser", "module", "jsnext:main", "jsnext"],
      extensions: [".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"],
      preserveSymlinks: false,
    },
    plugins: [],
    css: {},
    esbuild: {},
    server: {
      host: "localhost",
      port: 5173,
      strictPort: false,
      open: false,
      proxy: {},
      cors: true,
      headers: {},
      fs: {
        strict: true,
        allow: [],
        deny: [".env", ".env.*", "*.{crt,pem}"],
      },
      origin: "http://localhost:5173",
      hmr: true,
      watch: {},
      middlewareMode: false,
      sourcemapIgnoreList: () => false,
      preTransformRequests: true,
    },
    build: {
      target: ["es2020", "edge88", "firefox78", "chrome87", "safari14"],
      modulePreload: { polyfill: true },
      outDir: "dist",
      assetsDir: "assets",
      assetsInlineLimit: 4096,
      cssCodeSplit: true,
      cssTarget: ["es2020", "edge88", "firefox78", "chrome87", "safari14"],
      cssMinify: true,
      sourcemap: false,
      rollupOptions: {},
      minify: "esbuild",
      write: true,
      emptyOutDir: true,
      copyPublicDir: true,
      manifest: false,
      lib: false,
      ssr: false,
      ssrManifest: false,
      reportCompressedSize: true,
      chunkSizeWarningLimit: 500,
      watch: null,
      commonjsOptions: { include: [/node_modules/] },
      dynamicImportVarsOptions: { warnOnError: true, exclude: [/node_modules/] },
    },
    preview: {
      host: "localhost",
      port: 4173,
      strictPort: false,
      open: false,
      proxy: {},
      cors: true,
      headers: {},
    },
    optimizeDeps: {
      include: [],
      exclude: [],
      disabled: false,
      esbuildOptions: {},
      holdUntilCrawlEnd: true,
      entries: [],
      force: false,
      noDiscovery: false,
      needsInterop: [],
    },
    ssr: {
      external: [],
      noExternal: [],
      target: "node",
      resolve: {
        conditions: [],
        externalConditions: [],
      },
      optimizeDeps: {
        include: [],
        exclude: [],
        disabled: "build",
        esbuildOptions: {},
        holdUntilCrawlEnd: true,
        entries: [],
        force: false,
        noDiscovery: false,
        needsInterop: [],
      },
    },
    worker: {
      format: "iife",
      plugins: () => [],
      rollupOptions: {},
    },
    appType: "spa",
    experimental: {},
    legacy: {},
    logger: mockLogger,
    cacheDir: "node_modules/.vite",
    publicDir: "public",
    assetsInclude: () => false,
    isWorker: false,
    mainConfig: null,
    isProduction: false,
    html: {},
    ...overrides,
  } as unknown as ResolvedConfig
}

/**
 * Creates a mock Litestar config JSON object.
 */
export function createMockLitestarConfig(overrides: Record<string, unknown> = {}) {
  return {
    bundleDir: "public",
    hotFile: "hot",
    proxyMode: "vite",
    port: 5173,
    protocol: "http",
    host: "localhost",
    ...overrides,
  }
}
