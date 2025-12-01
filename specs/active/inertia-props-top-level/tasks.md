- Planning
  - Confirm scope: deliver top-level props while staying on Litestar's normal serializer path; avoid custom msgspec/attrs/dataclass/pydantic bypass checks.
  - Prefer minimal server-side change; keep a fallback option for a small frontend wrapper only if serializer-safe server change is too invasive.
  - Decide on migration note and any feature flag.

- Research
  - Inspect `src/py/litestar_vite/inertia/response.py` (and helpers) to map current prop assembly and where `content` is introduced.
  - Locate JS bootstraps per adapter to see if they assume nested `content` or call `unwrapPageProps`.
  - Review example apps (`examples/*inertia*`) for prop access patterns.

- Design
  - Specify merge order for shared props, lazy props, and route content (precedence rules, explicit `content` handling) without altering serializer contracts.
  - Decide fate of `unwrapPageProps` (remove, gate, no-op) with compatibility notes; consider earlier lifecycle hook if frontend wrapping is chosen.

- Implementation (Python)
  - Update Inertia response construction to spread `content` into `props` before serialization while honoring explicit `content` keys and leaving Litestar serializer behavior intact.
  - Add/adjust unit tests for serialization and key precedence.

- Implementation (JavaScript)
  - Adjust Inertia adapter boot code for Svelte, React, Vue to assume top-level props; remove redundant unwrapping if present.
  - Update helper exports if behavior changes.

- Examples & Docs
  - Update Inertia examples to use top-level props; add note if `content` key was referenced.
  - Add changelog/guide snippet describing the shape change and migration guidance.

- Testing
  - Python: pytest for InertiaResponse payload shape and merge precedence.
  - JS: Vitest (or adapter-level tests) verifying boot receives top-level props for initial load and simulated SPA navigation.
  - Smoke run example(s) or minimal adapter integration to ensure navigation works.

- Quality Gate
  - Run `make lint`, `make test`, and relevant adapter tests; ensure coverage stays ≥ current baseline for touched modules.
  - Capture before/after payload snapshots for PR description.
