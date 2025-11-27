# Recovery Guide – typed-routes-proxy

## Context
- Feature: Single-source typed routes + one-port Vite proxy
- Key dirs: `src/py/litestar_vite`, `src/js/src`, `specs/active/typed-routes-proxy`
- Generated artifacts target: `src/generated/routes.json`, `src/generated/openapi.json`, `src/generated/routes.ts`

## Resume Checklist
1. Re-read `specs/active/typed-routes-proxy/prd.md` and `tasks.md`.
2. Confirm latest code state: `git status -sb`.
3. Proxy is default: internal loopback Vite with hotfile `public/hot`, `_PROXY_PATH_PREFIXES` set; direct/two-port remains opt-in.
4. Defaults aligned: asset base `/static/`, generated outputs `src/generated/openapi.json`, `src/generated/routes.json`, `src/generated/routes.ts`.
5. Types default ON; JS plugin debounces openapi-ts and emits routes.ts when routes.json exists. Route/type inference trimmed on Python side; rely on OpenAPI for detailed types.
6. Tests currently green (`npm test`, `uv run pytest -q`); warning filters centralized in `pyproject.toml`.

## Quick Pointers
- Proxy mode is default; direct mode still supported.
- openapi-ts is optional; warn not fail when missing.
- Keep Optional/Union style typing (stringified) per project standard.
