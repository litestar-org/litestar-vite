# Doctor CLI & Troubleshooting

Because a polyglot Python + Vite stack spans `app.py`, `.litestar.json`, `vite.config.ts`, `package.json`, and generated TypeScript artifacts, subtle mismatches in directory paths or environment variables are the most common source of setup friction.

`litestar assets doctor` inspects your live `ViteConfig` alongside your frontend workspace and runs **9 automated health checks**.

---

## Running the Doctor Command

```bash
litestar assets doctor
```

To automatically repair fixable issues (such as stale `.litestar.json` bridges or mismatched `vite.config.ts` settings) without interactive prompts:

```bash
litestar assets doctor --fix --no-prompt
```

For CI pipelines, run `--check` with `--runtime-checks` to exit with status `1` if any health check fails:

```bash
litestar assets doctor --check --runtime-checks
```

---

## Diagnostic Checks

| Check | What It Verifies | Common Fix |
| --- | --- | --- |
| **1. `vite.config` Presence & Plugin** | `vite.config.ts` / `.js` exists and registers `litestar-vite-plugin` | Run `litestar assets init` or add `litestar({ input: [...] })` to `vite.config.ts` |
| **2. Path Synchronization** | `bundle_dir`, `resource_dir`, and `asset_url` in `vite.config.ts` do not conflict with `PathConfig` | Remove hardcoded `base` / `build.outDir` overrides in `vite.config.ts` so `.litestar.json` governs them |
| **3. `.litestar.json` Bridge Freshness** | `.litestar.json` exists and matches the current `ViteConfig` serialization | Run `litestar assets doctor --fix` or start the app once |
| **4. Package Dependencies** | `package.json` declares `vite >= 7.0.0` and `litestar-vite-plugin` matching the installed Python package version | Run `npm install -D litestar-vite-plugin@latest vite@^7.0.0` |
| **5. Entrypoints & Root Template** | Configured entrypoints (`src/main.tsx`, `index.html`, or `InertiaConfig.root_template`) exist on disk | Check `PathConfig.resource_dir` and `InertiaConfig.root_template` |
| **6. Production Manifest & Hotfile** | In `dev_mode=False`, verifies `<bundle_dir>/.vite/manifest.json` exists and no stale `hot` file is left behind | Run `litestar assets build` and remove stale `<bundle_dir>/hot` |
| **7. TypeGen Artifacts** | When `TypeGenConfig` is enabled, checks `openapi.json`, `routes.json`, and `schemas.ts` exist | Run `litestar assets generate-types` |
| **8. Inertia Script-Element Alignment** | When `InertiaConfig.use_script_element=True`, checks that Inertia v2 client entrypoints enable `useScriptElementForInitialPage: true` | Add `defaults: { future: { useScriptElementForInitialPage: true } }` to `createInertiaApp()` |
| **9. Runtime & Environment Alignment** | Detects `RuntimeConfig.executor` / lockfile mismatches (`detect_runtime_marker`) and deprecated `VITE_PROXY_MODE=direct` overrides | Omit `RuntimeConfig.executor` to auto-detect from your lockfile and unset `VITE_PROXY_MODE=direct` |

---

## Common Symptoms & Solutions

### Missing Manifest on Startup

**Cause**: `dev_mode=False` (the default when running `litestar run` without `--reload` or `--debug`), and `litestar assets build` has not been run yet.

**Solution**:

- For local development: run `litestar run --reload` (which auto-enables `dev_mode=True`) or set `VITE_DEV_MODE=true`.
- For production: run `litestar assets build` before starting the server.

### Blank Initial Inertia Page

**Cause**: `InertiaConfig.use_script_element` defaults to `True` (emitting `<script type="application/json" data-page="app">`), while `@inertiajs/*` v2 defaults to reading the legacy `data-page` HTML attribute unless `useScriptElementForInitialPage: true` is set.

**Solution**: Pass `defaults: { future: { useScriptElementForInitialPage: true } }` to `createInertiaApp({ ... })` in both your browser entrypoint and SSR entrypoint.

### WebSocket HMR Disconnects Behind Docker or Reverse Proxy

**Cause**: Container port mappings or reverse proxies stripping WebSocket `Upgrade` headers or forwarding untrusted `X-Forwarded-Proto` headers.

**Solution**: Set `LITESTAR_TRUSTED_PROXIES="*"` (or your proxy CIDR) in your container environment and ensure your reverse proxy forwards `Upgrade` and `Connection` headers on `/vite-hmr`.
