# Feature: Non-Breaking DX and Feature Enhancements

## Overview

This document outlines a series of non-breaking enhancements for the `litestar-vite` library. The primary goal is to improve the developer experience (DX), increase configuration flexibility, provide more robust error handling, and introduce new features that align with best practices seen in mature Vite integrations in other ecosystems (e.g., Laravel).

These changes are designed to be additive. They will not alter the existing public API, ensuring full backward compatibility for current users. The proposed enhancements are grouped into five main categories:

1. **Configuration & Dev Server Enhancements**: Making the `ViteConfig` more powerful and the development server process more reliable.
2. **Developer Experience & Tooling**: Introducing specific exceptions for easier debugging, adding a new CLI command for project diagnostics, and verifying existing CLI functionality.
3. **Advanced Asset Management**: Adding support for referencing any Vite-processed asset (images, fonts, etc.), not just entry points.
4. **Inertia.js Power-ups**: Introducing support for lazy-loaded props (partial reloads), a standard feature in the Inertia.js protocol.
5. **JS/TS Helper Library**: Creating TypeScript definitions and expanding the helper library to improve frontend development.

## Problem Statement

While `litestar-vite` provides a solid foundation for integrating Litestar with Vite, its developer experience can be improved, and its feature set can be expanded to better support complex, modern frontend applications.

Currently, users face the following challenges:

- **Limited Configuration**: The `ViteConfig` object is minimal, forcing users to rely on environment variables or custom scripts for setups involving CDNs, custom asset URLs, or complex build commands.
- **Generic Error Messages**: When something goes wrong (e.g., the manifest is not found or the Vite process fails), the generic `LitestarViteError` provides little context, making debugging difficult and time-consuming.
- **Basic Asset Handling**: The library only provides a helper for loading entry points (JS/CSS). There is no built-in way to get the versioned URL of other assets like images or fonts that are processed by Vite, a common requirement.
- **Basic Inertia Support**: The Inertia.js integration lacks advanced features like lazy prop loading, which is crucial for optimizing page load performance in data-heavy applications.
- **No TypeScript Support**: The frontend helper library lacks TypeScript definitions (Issue #71), which is a major DX issue for modern frontend development.

These limitations can increase the learning curve and lead to friction during development. By addressing them with non-breaking additions, we can significantly enhance the library's power and ease of use.

## Acceptance Criteria

### Epic 1: Configuration & Dev Server Enhancements

- [ ] A `health_check: bool` option can be added to `ViteConfig`, defaulting to `True`. When enabled, the `VitePlugin` will probe the Vite dev server on startup and wait until it's responsive before allowing the Litestar app to proceed.
- [ ] A `base_url: str | None` option can be added to `ViteConfig`. If set, all production asset URLs will be prefixed with this URL, enabling easy CDN integration.
- [ ] An `asset_url: str | None` option can be added to `ViteConfig`. If set, all development asset URLs will be proxied from this URL, improving HMR reliability in complex network environments (e.g., Docker).
- [ ] The `VitePlugin` logs a clear warning message if `dev_mode` is `True` in an environment that appears to be for production (e.g., `LITESTAR_DEBUG` is not `True`).

### Epic 2: Developer Experience & Tooling

- [ ] A `ManifestNotFoundError` (subclass of `LitestarViteError`) is raised if the `manifest.json` file is not found when `dev_mode` is `False`.
- [ ] A `ViteProcessError` (subclass of `LitestarViteError`) is raised if the Vite dev server process fails to start or exits with a non-zero code.
- [ ] An `AssetNotFoundError` (subclass of `LitestarViteError`) is raised if a requested asset key does not exist in the manifest.
- [ ] A new CLI command, `litestar vite status`, is available.
- [ ] The `status` command successfully checks for `package.json`, `vite.config.ts`, and the production manifest (if not in dev mode), reporting success or failure for each check.
- [ ] Existing CLI commands are verified to be functional and provide clear output.

### Epic 3: Advanced Asset Management

- [ ] A new template callable named `vite_static` is available in the Jinja2 environment.
- [ ] In production (`dev_mode=False`), `vite_static('path/to/image.png')` returns the correctly versioned URL for the image from the `manifest.json`.
- [ ] In development (`dev_mode=True`), `vite_static('path/to/image.png')` returns the correct, un-versioned path to the asset (e.g., `/static/path/to/image.png`).
- [ ] The `vite_static` function raises `AssetNotFoundError` if the asset is not found in the manifest during production.

### Epic 4: Inertia.js Power-ups

- [ ] A new helper class, `DeferredProp`, is available in `litestar_vite.inertia.helpers`.
- [ ] When a prop in an `InertiaResponse` is wrapped in `DeferredProp`, it is not included in the initial page load response.
- [ ] When an Inertia partial reload request specifically asks for a deferred prop (via the `X-Inertia-Partial-Data` header), the response contains only that deferred prop's data.

### Epic 5: JS/TS Helper Library (Addresses Issue #71)

- [ ] A `d.ts` file is generated and included in the published `npm` package.
- [ ] The existing JS/TS helper functions are correctly typed.
- [ ] (Stretch Goal) A new helper function, `route()`, is added to the JS/TS library to resolve Litestar route URLs on the frontend.

## Technical Design

### 1. Configuration & Dev Server Enhancements

The `ViteConfig` class in `src/py/litestar_vite/config.py` will be updated with the new optional fields (`health_check`, `base_url`, `asset_url`), all with default values of `None` or `True` to ensure no breaking changes.

The `VitePlugin` in `src/py/litestar_vite/plugin.py` will be modified. In its `on_app_init` method, it will read these new config values. The `server_lifespan` context manager will be updated to include the health check logic, where it will use an HTTP client (like `httpx`) to poll the Vite dev server URL in a loop with a timeout. The logic for generating asset URLs in `ViteAssetLoader` will be updated to respect the `base_url` and `asset_url` settings.

**Code Sample (`ViteConfig`)**:

```python
# src/py/litestar_vite/config.py

class ViteConfig(BaseModel):
    # ... existing fields
    health_check: bool = True
    base_url: str | None = None
    asset_url: str | None = None
```

### 2. Developer Experience & Tooling

New exception classes (`ManifestNotFoundError`, `ViteProcessError`, `AssetNotFoundError`) will be defined in `src/py/litestar_vite/exceptions.py`.

- `ViteAssetLoader` will be modified to raise `ManifestNotFoundError` in its constructor if the manifest file doesn't exist in production mode. It will raise `AssetNotFoundError` if a key is missing.
- `ViteProcess` will be updated to raise `ViteProcessError` if the `subprocess.Popen` call fails or if the process terminates unexpectedly.

A new function for the `status` command will be added to `src/py/litestar_vite/cli.py`. This function will perform a series of file existence and connectivity checks and print formatted output to the console. Existing CLI commands will be verified for functionality.

### 3. Advanced Asset Management

A new method will be added to `ViteAssetLoader` to resolve static asset paths.

```python
# src/py/litestar_vite/loader.py

class ViteAssetLoader:
    # ...
    def get_static_asset(self, name: str) -> str:
        """Gets the URL for a static, non-entry asset."""
        if self._config.dev_mode:
            # In dev mode, return the path relative to the static dir
            return str(self._config.static_path / name)

        # In prod mode, look it up in the manifest
        manifest = self._read_manifest()
        asset_entry = manifest.get(name)
        if not asset_entry or not asset_entry.get("file"):
            raise AssetNotFoundError(f"Static asset '{name}' not found in manifest.")

        url = f"{self._config.hot_file.parent.as_posix()}/{asset_entry['file']}"
        if self._config.base_url:
            return f"{self._config.base_url}{url}"
        return url
```

The `VitePlugin` will register a new template callable `vite_static` that calls this loader method.

### 4. Inertia.js Power-ups

A new class `DeferredProp` will be created in `src/py/litestar_vite/inertia/helpers.py`.

The `InertiaResponse.to_asgi_response` method in `src/py/litestar_vite/inertia/response.py` will be updated. It will inspect the `InertiaRequest` headers. If it's a partial reload (`X-Inertia-Partial-Data`), it will filter the props dictionary, resolving only the requested `DeferredProp` instances. For initial loads, it will exclude any props that are instances of `DeferredProp`.

### 5. JS/TS Helper Library

The work will be done in the `src/js` directory. A build script will be added to `src/js/package.json` to run `tsc` to generate the type definitions. The `tsconfig.json` will be configured to emit declaration files.

## Testing Strategy

- **Unit Tests**:
  - Test that `ViteConfig` correctly initializes with new fields and defaults.
  - Test that `ViteAssetLoader` raises the new specific exceptions under mocked failure conditions.
  - Test the logic of the `get_static_asset` method in both dev and prod mode.
  - Test the `DeferredProp` filtering logic in `InertiaResponse`.
- **Integration Tests**:
  - Create a test Litestar application with the enhanced `ViteConfig` and verify asset URLs are generated correctly with `base_url`.
  - Write an integration test for the `litestar vite status` CLI command using `CliRunner`.
  - Write an integration test to verify the functionality of existing CLI commands.
  - Write an integration test with a real Vite manifest containing static assets and verify the `vite_static` template callable works.
  - Write an integration test for Inertia partial reloads.
- **Frontend Tests**:
  - Add a test to `src/js/tests` to confirm the TypeScript types can be consumed correctly.
- **Coverage**: Ensure all new and modified code has >90% test coverage.

## Risks & Mitigations

- **Risk 1**: The dev server health check could add a noticeable delay to application startup.
  - **Mitigation**: Implement a reasonable timeout (e.g., 10-15 seconds) and make the feature easy to disable with the `health_check: bool` flag.
- **Risk 2**: Incorrectly parsing the Vite manifest could lead to broken asset paths.
  - **Mitigation**: The logic must be thoroughly unit-tested with various real-world manifest file examples to handle all edge cases, including assets with and without CSS or other imports.

## Dependencies

- No new external library dependencies are anticipated. The health check can be implemented using the existing `httpx` dependency if available, or the standard library's `http.client`.
