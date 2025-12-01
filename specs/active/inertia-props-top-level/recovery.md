## Recovery Guide

### Current State
- PRD drafted for fixing Inertia props nesting; slug `inertia-props-top-level`.
- Tasks outlined across planning, research, implementation, testing, and docs.

### Next Steps
1) Read `src/py/litestar_vite/inertia/response.py` (and related helpers) to pinpoint where `content` is injected.
2) Inspect JS Inertia adapter bootstraps (Svelte/React/Vue) for `unwrapPageProps` usage and assumptions.
3) Decide merge precedence rules and whether to keep a compatibility no-op for `unwrapPageProps`.
4) Implement server-side flattening; add unit tests.
5) Align adapters and examples; add JS tests for SPA navigation props shape.
6) Run `make lint` and `make test`; note coverage and payload snapshots for PR notes.

### Open Questions
- Need feature flag or version note for the response shape change?
- Keep `unwrapPageProps` as a no-op for backward compatibility?

### Artefacts
- PRD: `specs/active/inertia-props-top-level/prd.md`
- Tasks: `specs/active/inertia-props-top-level/tasks.md`
