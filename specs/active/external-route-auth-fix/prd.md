# PRD: External Mode Static Router Auth Fix

## Overview
- **Slug**: external-route-auth-fix
- **Created**: 2025-12-10
- **Status**: Implemented
- **GitHub Issue**: [#147](https://github.com/litestar-org/litestar-vite/issues/147)

## Problem Statement

When using `mode="external"` for non-Vite frameworks (Angular CLI, Next.js, Create React App, etc.), the auto-registered static files router in production mode was missing critical configuration options:

1. **Missing `opt={"exclude_from_auth": True}`** - Authentication middleware intercepts static file requests, causing 401 errors for JS, CSS, and images.

2. **Hardcoded `path="/"`** - Ignores `asset_url` from PathConfig, breaking configurations where assets are served from different paths (e.g., `/web/` for Angular apps).

3. **Missing `include_in_schema=False`** - Static file routes pollute the OpenAPI schema unnecessarily.

4. **Duplicate code** - External mode had a separate static files block instead of using `_configure_static_files()`.

## Solution Implemented

**Simplified approach**: Instead of having a separate external mode block, we made `_configure_static_files()` mode-aware:

### Changes to `plugin.py`

1. **`_configure_static_files()` now uses `html_mode=True` for external mode in production**:
   ```python
   # External mode (Angular CLI, etc.) uses html_mode=True for SPA fallback in production
   html_mode = self._config.mode == "external" and not self._config.is_dev_mode
   ```

2. **Skip static files for external mode in dev** (proxy handles everything):
   ```python
   skip_static = self._config.mode == "external" and self._config.is_dev_mode
   if self._config.set_static_folders and not skip_static:
       self._configure_static_files(app_config)
   ```

3. **Removed duplicate external mode block** - no longer needed since `_configure_static_files()` handles all cases.

### Changes to `examples/angular-cli/app.py`

Added explicit `asset_url="/"` for external mode SPA:
```python
paths=PathConfig(root=here, bundle_dir=dist_dir, asset_url="/"),
```

## Key Benefits

1. **Single code path** - `_configure_static_files()` handles all modes consistently
2. **Auth exclusion** - Already present in `_configure_static_files()` (`opt={"exclude_from_auth": True}`)
3. **Respects `asset_url`** - Uses configured path instead of hardcoded `/`
4. **SPA fallback** - `html_mode=True` for external mode production serves index.html for non-file routes
5. **No dev mode conflicts** - Static files skipped in dev (proxy handles everything)

## Acceptance Criteria

- [x] External mode static router includes `opt={"exclude_from_auth": True}`
- [x] External mode static router uses `self._config.asset_url`
- [x] External mode static router includes `include_in_schema=False`
- [x] `html_mode=True` for external mode in production (SPA fallback)
- [x] Static files skipped for external mode in dev (proxy handles it)
- [x] All existing tests pass
- [x] Linting clean

## Files Modified

| File | Changes |
|------|---------|
| `src/py/litestar_vite/plugin.py` | Made `_configure_static_files()` mode-aware, removed duplicate block |
| `examples/angular-cli/app.py` | Added `asset_url="/"` for external mode |

## Usage

For external mode (Angular CLI, Next.js, etc.):

```python
ViteConfig(
    mode="external",
    paths=PathConfig(
        bundle_dir=Path("dist"),
        asset_url="/",  # Required for SPA at root
    ),
    runtime=RuntimeConfig(
        external_dev_server=ExternalDevServer(
            target="http://localhost:4200",
            command=["npm", "run", "start"],
        ),
    ),
)
```
