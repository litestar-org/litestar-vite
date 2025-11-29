# Recovery Guide: Vite Asset Deployment to CDN with fsspec

## Current State

**Phase**: Planning Complete
**Status**: Ready for Implementation
**Last Updated**: 2025-11-29

The PRD and task breakdown are complete. No code has been written yet.

## Files Created

| File | Status | Description |
|------|--------|-------------|
| `specs/active/vite-deploy-cdn/prd.md` | Complete | Product Requirements Document |
| `specs/active/vite-deploy-cdn/tasks.md` | Complete | Task breakdown |
| `specs/active/vite-deploy-cdn/recovery.md` | Complete | This file |

## Files To Be Modified

| File | Changes Needed |
|------|----------------|
| `src/py/litestar_vite/deploy.py` | **New**: DeployConfig, ViteDeployer |
| `src/py/litestar_vite/config.py` | Add `deploy` field |
| `src/py/litestar_vite/cli.py` | Add `vite_deploy` command |
| `src/py/litestar_vite/__init__.py` | Export DeployConfig |
| `src/py/tests/unit/test_deploy.py` | **New**: Unit tests |

## Next Steps

1. **Start with Phase 2**: Create the DeployConfig dataclass
   ```bash
   # Create the deploy.py file with DeployConfig
   ```

2. **Integrate into ViteConfig**: Add deploy field to config.py

3. **Implement core logic**: ViteDeployer class with sync logic

4. **Add CLI command**: deploy command in cli.py

5. **Write tests**: Unit and integration tests

## Key Design Decisions

1. **Command name**: `litestar assets deploy` (fits existing pattern)

2. **Storage configuration**: fsspec URL string + options dict
   ```python
   DeployConfig(
       storage_backend="s3://bucket/path",
       storage_options={"key": "...", "secret": "..."},
   )
   ```

3. **Sync strategy**: Upload new files first, then delete orphaned (safer)

4. **Change detection**: By file size (not content hash, for performance)

5. **Build integration**: Set `VITE_BASE_URL` env var before build

## Context for Resumption

### Why fsspec?
Litestar already uses fsspec for static file serving (`create_static_files_router` accepts a `file_system` parameter). Using fsspec for deployment provides consistency and supports the same backends.

### Why not content hash comparison?
Reading all files to compute content hashes would be slow for large deployments. Vite already puts content hashes in filenames, so size comparison is sufficient for detecting changes.

### Environment Variables
- `VITE_BASE_URL` - Used during Vite build to set asset base path
- `VITE_DEPLOY_STORAGE` - Optional default storage backend
- Cloud provider credentials (AWS_ACCESS_KEY_ID, etc.) - Standard fsspec auth

## Research Completed

1. **Litestar fsspec integration**: Documented in [Litestar static files docs](https://docs.litestar.dev/latest/usage/static-files)

2. **fsspec upload methods**: `put()`, `upload()`, and async variants

3. **Django collectstatic pattern**: Collect → Sync → Clean workflow

4. **Existing CLI structure**: Commands follow `vite_group.command` pattern

## Potential Challenges

1. **fsspec provider installation**: Users need to install s3fs/gcsfs/etc. separately
   - Solution: Clear error messages with install instructions

2. **Large file uploads**: Could timeout
   - Solution: fsspec handles chunked uploads internally

3. **Parallel uploads**: Could improve performance
   - Solution: Consider in future iteration using async methods
