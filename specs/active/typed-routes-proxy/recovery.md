# Recovery Guide – typed-routes-proxy

## Context
- Feature: Single-source typed routes + one-port Vite proxy
- Key dirs: `src/py/litestar_vite`, `src/js/src`, `specs/active/typed-routes-proxy`
- Generated artifacts target: `src/generated/routes.json`, `src/generated/openapi.json`, `src/generated/routes.ts`

## Resume Checklist
1. Re-read `specs/active/typed-routes-proxy/prd.md` and `tasks.md`.
2. Confirm latest code state: `git status -sb`.
3. If proxy work in progress, note internal port/env assumptions.
4. Ensure defaults remain aligned: asset base `/static/`, generated paths `src/generated/*`.

## Quick Pointers
- Proxy mode is default; direct mode still supported.
- openapi-ts is optional; warn not fail when missing.
- Keep Optional/Union style typing (stringified) per project standard.
