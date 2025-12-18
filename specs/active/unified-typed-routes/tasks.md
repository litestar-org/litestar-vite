# Tasks: Inertia-Compatible Route Objects

## Phase 1: Determinism Fix ✓

- [x] Sort handlers in `iter_route_handlers()` by (path, handler_name)
- [x] Prefer GET handlers when multiple handlers share a component
- [x] All tests pass

## Phase 2: Add `method` to Route Data ✓

- [x] Add `pick_primary_method()` helper in `_routes.py`
- [x] Add `method` field to `generate_routes_json()` output
- [x] Add `method` field to `generate_routes_ts()` output (on routeDefinitions)

## Phase 3: route() Function ✓

- [x] Keep `route()` returning string (backward compatible)
- [x] Update TypeScript RouteDefinition interface to include `method`
- [x] Method accessible via `routeDefinitions[name].method`

## Phase 4: Remove Module Augmentation ✓

- [x] Update page-props generator to use direct imports
- [x] Update user stub template with UserExtensions/SharedPropsExtensions
- [x] Update inertia-types.ts base documentation

## Phase 5: Testing ✓

- [x] All unit tests pass
- [x] Lint checks pass (mypy, pyright, ruff)
- [x] JS package builds successfully
