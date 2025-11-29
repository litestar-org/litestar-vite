# Litestar Vite Plugin (JS)

Vite plugin that pairs with the Litestar Python backend. It writes the hotfile Vite URL, respects `assetUrl`, and can trigger type generation when the backend exports OpenAPI/routes.

## Install
```bash
npm install @litestar/vite-plugin
```

## Vite config (vite.config.ts)
```ts
import { defineConfig } from "vite"
import litestar from "@litestar/vite-plugin"

export default defineConfig({
  plugins: [
    litestar({
      input: ["src/main.ts"],
      assetUrl: "/static/",
      bundleDirectory: "public/dist",
      types: { enabled: true, output: "src/types/api", generateZod: true },
    }),
  ],
})
```

## Options (essentials)
- `input`: entry file(s) for Vite.
- `assetUrl`: must match Python `ViteConfig.asset_url` (default `/static/`).
- `bundleDirectory`: where build output and manifest live (default `public/dist`).
- `resourceDirectory`: source dir for full-reload watching (default `resources`).
- `hotFile`: path to write dev URL (default `${bundleDirectory}/hot`).
- `refresh`: paths or config for vite-plugin-full-reload.
- `types`: `false` or { `enabled`, `output`, `openapiPath`, `routesPath`, `generateZod`, `generateSdk`, `debounce` }.

## Dev / prod notes
- Dev: writes `hot` file; Litestar proxy reads it to forward HTTP + HMR.
- Prod: serve assets via manifest in `bundleDirectory`; keep `assetUrl` in sync with backend.

## Attribution
This plugin’s design is heavily inspired by the Laravel Vite plugin: https://github.com/laravel/vite-plugin.

## Links
- Docs: https://litestar-org.github.io/litestar-vite/
- Repo: https://github.com/litestar-org/litestar-vite
