# Implementation Tasks: Non-Breaking DX and Feature Enhancements

## Phase 1: Planning & Research ✓

- [x] PRD created
- [x] Research documented
- [x] Workspace setup
- [x] Deep analysis completed
- [x] GitHub Issues analyzed and incorporated

## Phase 2: Core Implementation

### Epic 1: Configuration & Dev Server Enhancements
- [ ] **`ViteConfig`**: Modify `src/py/litestar_vite/config.py` to add `health_check: bool`, `base_url: str | None`, and `asset_url: str | None`. Ensure they have correct default values.
- [ ] **`VitePlugin`**: Update `on_app_init` in `src/py/litestar_vite/plugin.py` to handle the new config values.
- [ ] **Health Check**: Implement the dev server health check logic within the `server_lifespan` context manager in `plugin.py`. Use `httpx` or a standard library equivalent.
- [ ] **Asset URL Logic**: Update `ViteAssetLoader` in `src/py/litestar_vite/loader.py` to use `base_url` for production assets and `asset_url` for development assets.
- [ ] **Security Warning**: Add the warning log message to the `VitePlugin` when `dev_mode` is enabled in a potential production environment.

### Epic 2: Developer Experience & Tooling
- [ ] **Custom Exceptions**: Define `ManifestNotFoundError`, `ViteProcessError`, and `AssetNotFoundError` in `src/py/litestar_vite/exceptions.py`.
- [ ] **Raise Exceptions**: Modify `ViteAssetLoader` and `ViteProcess` to raise these new, specific exceptions in the appropriate failure scenarios.
- [ ] **CLI Command**: Add the `status` command to `src/py/litestar_vite/cli.py`.
- [ ] **CLI Logic**: Implement the diagnostic checks (file existence, server connectivity) within the `status` command function.
- [ ] **Verify Existing CLI**: Verify the functionality of existing CLI commands, including the one previously reported in Issue #60.

### Epic 3: Advanced Asset Management
- [ ] **`ViteAssetLoader` Method**: Implement the `get_static_asset` method in `src/py/litestar_vite/loader.py`.
- [ ] **Template Callable**: In `VitePlugin`, register `vite_static` as a new template callable, linking it to the `get_static_asset` loader method.

### Epic 4: Inertia.js Power-ups
- [ ] **`DeferredProp` Helper**: Create the `DeferredProp` class in `src/py/litestar_vite/inertia/helpers.py`.
- [ ] **Response Logic**: Update `InertiaResponse.to_asgi_response` in `src/py/litestar_vite/inertia/response.py` to filter props based on the `X-Inertia-Partial-Data` header and `DeferredProp` instances.

### Epic 5: JS/TS Helper Library (Addresses Issue #71)
- [ ] **`tsconfig.json`**: Configure `src/js/tsconfig.json` to emit declaration files (`"declaration": true`).
- [ ] **Build Script**: Add a script to `src/js/package.json` to generate the type definitions (e.g., `"build:types": "tsc --emitDeclarationOnly"`).
- [ ] **Package Files**: Ensure the generated `.d.ts` files are included in the `files` array in `src/js/package.json`.

## Phase 3: Testing (Auto via /test command)

- [ ] **Unit Tests**:
    - [ ] Write unit tests for the new `ViteConfig` fields.
    - [ ] Write unit tests to verify that the correct custom exceptions are raised.
    - [ ] Write unit tests for the `get_static_asset` method.
    - [ ] Write unit tests for the `InertiaResponse` prop filtering logic.
- [ ] **Integration Tests**:
    - [ ] Write an integration test for the `base_url` and `asset_url` functionality.
    - [ ] Write an integration test for the `litestar vite status` CLI command using `CliRunner`.
    - [ ] Write an integration test to verify the functionality of existing CLI commands, including the one previously reported in Issue #60.
    - [ ] Write an integration test with a real Vite manifest containing static assets and verify the `vite_static` template callable works.
    - [ ] Write an integration test for Inertia partial reloads.
- [ ] **Frontend Tests**:
    - [ ] Add a test to `src/js/tests` to confirm the TypeScript types can be consumed correctly.
- [ ] **Coverage**: Ensure all new and modified code has >90% test coverage.

## Phase 4: Documentation (Auto via /review command)

- [ ] Update `docs/usage/vite.rst` to document the new `ViteConfig` options.
- [ ] Add a new section to the documentation for "Advanced Asset Handling" explaining `vite_static`.
- [ ] Update `docs/reference/cli.rst` to document the new `vite status` command and confirm the functionality of existing CLI commands.
- [ ] Update `docs/usage/inertia.rst` to document `DeferredProp` and partial reloads.
- [ ] Add documentation for the JS/TS helper library, including the new TypeScript support.
- [ ] Ensure all new code has complete and accurate docstrings.

## Phase 5: Archival

- [ ] Workspace moved to `specs/archive/`
- [ ] `ARCHIVED.md` created
