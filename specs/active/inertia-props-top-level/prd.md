# Inertia Props Top-Level Fix — PRD

## Overview
Inertia.js props from Litestar Inertia endpoints are currently wrapped under a `content` key on the client for Svelte, React, and Vue adapters. This breaks SPA navigation because Inertia's internal XHR bypasses our Axios interceptor workaround; only the initial page load is auto-unwrapped. We need a server-side fix so props are delivered at the top level for all adapters and navigation paths.

## Problem Statement
When handlers return `InertiaResponse(content={...})`, the frontend receives:

- Current: `{ "props": { "content": { ... } } }`
- Expected: `{ "props": { ... } }`

Impact:
- Initial load: Works only because a JS helper unwraps on first render.
- SPA navigation: Fails—props stay nested, components see `props.content.*`, router events fire after render, and Axios interceptors do not run because Inertia uses its own client.

## Goals
- Deliver Inertia props at the top level for all adapters (Svelte, React, Vue) on both initial load and SPA navigation.
- Preserve `shared_props` and `lazy`/`error` helpers semantics.
- Keep backward compatibility for apps that already access `props.content` by ensuring explicit `content` keys still work if provided by the app.
- Add regression coverage in Python and JS.

## Non-Goals
- Changing Inertia protocol headers or version.
- Reworking adapter-specific component bootstrapping beyond props shape.
- Introducing a global Axios interceptor for Inertia (problem is server-side shape, not transport).

## Users / Affected Surfaces
- Inertia apps built with the litestar-vite adapters for Svelte, React, and Vue.
- Example projects: `examples/react-inertia`, `examples/vue-inertia`, `examples/svelte` (if using Inertia helper).

## Current Behavior
- Backend `InertiaResponse` merges `shared_props` and then nests route payload under `content`.
- JS helper `unwrapPageProps` runs only on initial boot; SPA navigations keep nested props because Inertia's XHR bypasses Axios interceptors and router hooks fire post-render.

## Proposed Direction (Preferred)
Play nicely with Litestar's normal serialization path—do not bypass msgspec/attrs/dataclass/pydantic handling. First choice is still a server-side fix that spreads `content` into `props` while staying inside Litestar's serializer pipeline. If that proves invasive, a narrowly scoped frontend wrapper (earlier in the Inertia lifecycle than current unwrap) is acceptable, but avoid duplicating serialization logic client-side.

Key design points:
- If the user explicitly sets a `content` key in their payload, it should appear as `props.content`, but the rest of the payload should still be top-level.
- `shared_props` and `lazy` values must merge without nesting changes.
- Preserve Litestar serialization behavior (no custom bypasses); continue using the framework's standard serializer hook points.
- No `from __future__ import annotations`; keep PEP 604 typing.

## Alternatives Considered
1) **Client interception**: find earlier Inertia lifecycle hook. Rejected—fragile, adapter-specific, still duplicates logic.
2) **Accept nesting**: force `props.content.*` in apps. Rejected—breaks Inertia expectations, surprises users, hurts DX.

## Acceptance Criteria
- Returning `InertiaResponse(content={"books": [...]})` produces response JSON where `props.books` exists and no auto-added `props.content` wrapper.
- Behavior is identical for initial page load and SPA navigation across Svelte, React, and Vue adapters/examples.
- Existing shared props and lazy props remain available at the top level with no naming collisions or regressions.
- Automated tests cover: Python serialization logic + JS adapter behavior (at least unit or integration per adapter).
- Documentation (guide or changelog) notes the shape change and migration note for apps that relied on `props.content`.

## Technical Notes / Scope
- Touchpoints: `src/py/litestar_vite/inertia/response.py` (or helper that builds payload), and any adapter boot code that assumed nesting.
- Remove or narrow `unwrapPageProps` usage to avoid double-processing; keep only if harmless.
- Verify examples under `examples/*-inertia*` still render and navigate with updated shape.

## Risks
- Breaking apps that intentionally used `props.content.*`; mitigate with migration note and honoring explicit `content` keys.
- Merging rules could overwrite keys if `content` and shared props collide; need deterministic precedence and tests.
- Adapter discrepancies (Svelte vs React vs Vue) if bootstraps diverge.

## Open Questions
- Do we need a feature flag or minor version bump for the response shape change?
- Should we keep `unwrapPageProps` as a no-op for backward compatibility or remove it?

## References
- Issue context from user report (Dec 2025): Inertia props nested under `content` breaks SPA navigation.
