# Tasks: Vite Asset Deployment to CDN with fsspec

## Phase 1: Planning ✓
- [x] Create PRD
- [x] Research Litestar fsspec integration
- [x] Research existing CLI commands
- [x] Identify affected components

## Phase 2: Configuration Layer

### Task 2.1: Create DeployConfig dataclass
- [ ] Create `src/py/litestar_vite/deploy.py`
- [ ] Define `DeployConfig` dataclass with fields:
  - `enabled: bool`
  - `storage_backend: str | None`
  - `storage_options: dict[str, object]`
  - `delete_orphaned: bool`
  - `include_manifest: bool`
  - `content_types: dict[str, str]`
- [ ] Add `__post_init__` for environment variable fallbacks
- [ ] Add docstrings following Google style

### Task 2.2: Integrate DeployConfig into ViteConfig
- [ ] Modify `src/py/litestar_vite/config.py`
- [ ] Add `deploy: Union[DeployConfig, bool] = False` field
- [ ] Handle bool shortcut in `__post_init__`
- [ ] Add `deploy_config` property for typed access
- [ ] Update `__all__` exports

### Task 2.3: Export DeployConfig publicly
- [ ] Update `src/py/litestar_vite/__init__.py`
- [ ] Add `DeployConfig` to `__all__`

## Phase 3: Core Sync Logic

### Task 3.1: Implement file inventory functions
- [ ] In `deploy.py`, add `collect_local_files(bundle_dir, manifest_path) -> dict[str, FileInfo]`
- [ ] Add `FileInfo` dataclass with `path`, `size`, `mtime`
- [ ] Parse manifest.json to ensure we only deploy built assets
- [ ] Handle missing manifest.json gracefully

### Task 3.2: Implement remote inventory function
- [ ] Add `collect_remote_files(fs, path) -> dict[str, FileInfo]`
- [ ] Use `fs.ls(path, detail=True)` for listing
- [ ] Handle empty directories and non-existent paths
- [ ] Normalize paths for cross-platform compatibility

### Task 3.3: Implement diff computation
- [ ] Add `compute_diff(local, remote, delete_orphaned) -> SyncPlan`
- [ ] `SyncPlan` dataclass with `to_upload`, `to_delete` lists
- [ ] Compare by file size (content hash would require reading all files)

### Task 3.4: Implement sync execution
- [ ] Add `ViteDeployer` class
- [ ] `sync(dry_run=False) -> SyncResult` method
- [ ] Upload files using `fs.put(lpath, rpath)`
- [ ] Delete files using `fs.rm(rpath)`
- [ ] Add `SyncResult` dataclass with stats
- [ ] Implement progress callbacks for CLI output

## Phase 4: CLI Command

### Task 4.1: Add deploy command structure
- [ ] In `cli.py`, add `@vite_group.command(name="deploy")`
- [ ] Add options: `--storage`, `--storage-option`, `--no-build`, `--dry-run`, `--no-delete`, `--verbose`
- [ ] Import `ViteDeployer` and `DeployConfig`

### Task 4.2: Implement build phase
- [ ] Set `VITE_BASE_URL` environment variable from config
- [ ] Call `executor.execute(build_command)` unless `--no-build`
- [ ] Handle build failures with clear error messages

### Task 4.3: Implement sync phase
- [ ] Initialize fsspec filesystem from config
- [ ] Call `ViteDeployer.sync()`
- [ ] Display progress using Rich console
- [ ] Print summary of changes

### Task 4.4: Implement dry-run mode
- [ ] Show what would be uploaded
- [ ] Show what would be deleted
- [ ] Exit without making changes

## Phase 5: Testing

### Task 5.1: Unit tests for DeployConfig
- [ ] Create `src/py/tests/unit/test_deploy.py`
- [ ] Test default values
- [ ] Test bool shortcut conversion
- [ ] Test environment variable fallbacks
- [ ] Test content_types defaults

### Task 5.2: Unit tests for file inventory
- [ ] Test `collect_local_files` with typical build output
- [ ] Test handling of missing manifest
- [ ] Test `collect_remote_files` with mock fsspec
- [ ] Test empty directories

### Task 5.3: Unit tests for diff computation
- [ ] Test new files detection
- [ ] Test modified files detection
- [ ] Test orphaned files detection
- [ ] Test `delete_orphaned=False` behavior

### Task 5.4: Unit tests for sync execution
- [ ] Test with `MemoryFileSystem`
- [ ] Test dry-run mode
- [ ] Test partial sync (only changed files)
- [ ] Test full sync with deletes

### Task 5.5: Integration tests
- [ ] Test full deploy workflow end-to-end
- [ ] Test CLI command with mock filesystem
- [ ] Test error handling for network failures

## Phase 6: Documentation

### Task 6.1: Update docstrings
- [ ] Ensure all public functions have Google-style docstrings
- [ ] Add examples in docstrings

### Task 6.2: Add CLI help text
- [ ] Write descriptive help for `deploy` command
- [ ] Add examples in command help

## Phase 7: Quality Gate

- [ ] All tests pass (`make test`)
- [ ] Linting clean (`make lint`)
- [ ] 90%+ coverage for new modules
- [ ] No anti-patterns (Optional, future annotations, class tests)
- [ ] Archive workspace

## Estimated Effort

| Phase | Tasks | Complexity |
|-------|-------|------------|
| Phase 2: Configuration | 3 tasks | Low |
| Phase 3: Sync Logic | 4 tasks | Medium |
| Phase 4: CLI Command | 4 tasks | Medium |
| Phase 5: Testing | 5 tasks | Medium |
| Phase 6: Documentation | 2 tasks | Low |
| Phase 7: Quality Gate | 1 task | Low |

## Dependencies

- fsspec (already transitive dependency)
- Optional provider packages (user installs as needed):
  - `s3fs` for AWS S3
  - `gcsfs` for Google Cloud Storage
  - `adlfs` for Azure Blob Storage
