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
