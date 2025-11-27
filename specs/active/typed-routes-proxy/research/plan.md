# Research Plan – typed-routes-proxy

## Questions to Answer
- Minimal HTTP + WS path set required to proxy Vite HMR reliably across frameworks.
- Default `@hey-api/openapi-ts` options: types-only vs fetch client + zod plugins.
- Best strategy to choose/bind an internal Vite dev port (fallbacks, env overrides).

## Sources
- Vite docs: dev server proxying and HMR paths.
- Litestar plugin patterns (existing guides in `specs/guides/`).
- Prior Jinja/HMR approach for reference.

## Deliverables
- Recommended proxy path list and test matrix.
- Chosen openapi-ts command/flags and failure-handling behavior.
- Port allocation approach with env knobs.
- Integration notes for Angular Vite scaffold (pending validation).

## Findings (2025-11-27)
- **HMR proxy path set:** Proxy both HTTP and WS for: `/@vite/client`, `/@react-refresh`, `/@vite/`, `/@id/`, `/@fs/`, `/node_modules/.vite/`, `/src/`, `/__vite_ping`, `/@vite/env`, plus the HMR websocket upgrade on the root (`/`, default) or custom `server.hmr.path` when set. Keep fallback to direct WS allowed by Vite but prefer forwarding WS to avoid browser error banners. (Refs: Vite server.hmr docs + reverse proxy issues.)
- **openapi-ts defaults:** Run `npx @hey-api/openapi-ts -i src/generated/openapi.json -o src/generated/api` with **types-only** baseline. Optional flags: `--client fetch` when `generateSdk` is true; `--plugins @hey-api/schemas @hey-api/types` when `generateZod` is true. Missing dependency should warn once and skip generation (existing behavior in JS plugin).
- **Internal port strategy:** Bind internal Vite dev server to `127.0.0.1` using an ephemeral free port chosen by binding to port 0, then persist in the hotfile for reuse by the proxy. Allow overrides: `VITE_INTERNAL_PORT` (explicit), `VITE_PORT` (existing), and config field; honor `server.hmr.port/clientPort` when provided to keep HMR URL stable through proxy. If chosen port collides at start, retry a few times before surfacing a clear error.
