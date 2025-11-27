# Recovery Guide – Angular Integration

## Context
- Goal: Add Angular support (Vite-based and Angular CLI-based) with single-port proxy/HMR default.
- Status: In progress; defaults aligned to `/static/`, proxy baseline ready.
- Key dirs: `specs/active/angular-integration`, `src/py/litestar_vite/templates/` (to add Angular templates), JS plugin already single-port friendly.

## Resume Checklist
1) Re-read `specs/active/angular-integration/prd.md` and `tasks.md`.
2) Confirm working tree: `git status -sb`.
3) Remember: types are enabled by default; asset base `/static/`; hotfile path `public/hot`; proxy is default.
4) Plan next actions:
   - Add `FrameworkType.ANGULAR` (+ optional `ANGULAR_CLI`) and templates.
   - Validate Vite-based Angular with `@analogjs/vite-plugin-angular` under single-port proxy/HMR (proxy paths now include `/vite-hmr` and `/@analogjs/`).
   - Keep Angular CLI path as non-Vite, proxy via Angular dev server if used.
5) Tests currently green (`npm test`, `uv run pytest -q`); warning filters in `pyproject.toml`.

## Quick Pointers
- Use standalone Angular components (Angular 18+).
- Ensure Vite config uses proxy target via hotfile and base `/static/`.
- Generated routes/types live in `src/generated/*`; JS plugin already emits `routes.ts`.
