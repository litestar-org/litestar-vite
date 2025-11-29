# PRD: Vite Asset Deployment to CDN with fsspec

## Overview
- **Slug**: vite-deploy-cdn
- **Created**: 2025-11-29
- **Status**: Draft

## Problem Statement

Django users benefit from `collectstatic` paired with `django-storages`, which allows them to build and deploy static assets directly to cloud storage (S3, GCS, Azure) with a single command. This enables CDN-backed asset serving, improving performance and reducing server load.

Currently, litestar-vite users must manually:
1. Build assets with the correct CDN base URL
2. Upload built assets to their storage provider
3. Clean up orphaned files from previous builds
4. Ensure proper cache headers are set

This manual process is error-prone and doesn't leverage Litestar's existing fsspec integration for static file serving.

## Goals

1. **Single Command Deployment**: Provide a `litestar assets deploy` CLI command that builds and syncs assets to remote storage in one step
2. **fsspec Integration**: Leverage Litestar's existing fsspec support to work with any storage backend (S3, GCS, Azure, SFTP, etc.)
3. **Smart Sync**: Only upload changed files and optionally delete orphaned files from remote storage
4. **CDN-Ready Builds**: Automatically configure Vite's `base` URL for CDN asset serving
5. **Production Safety**: Provide dry-run mode and clear progress output

## Non-Goals

- Implementing CDN invalidation (provider-specific, out of scope)
- Managing CDN configuration (DNS, SSL, etc.)
- Replacing Litestar's static file serving (this is deployment-only)
- Supporting non-fsspec storage backends

## Acceptance Criteria

- [ ] New `DeployConfig` dataclass with storage backend configuration
- [ ] `ViteConfig.deploy` property for CDN deployment settings
- [ ] `litestar assets deploy` CLI command that:
  - [ ] Builds frontend with correct CDN base URL
  - [ ] Syncs built assets to remote storage via fsspec
  - [ ] Deletes orphaned files (configurable)
  - [ ] Shows progress and summary
- [ ] Support for `--dry-run` mode to preview changes
- [ ] Support for `--no-build` to deploy existing build
- [ ] Support for `--no-delete` to preserve orphaned files
- [ ] Clear error messages for missing dependencies
- [ ] Unit tests with 90%+ coverage
- [ ] Integration tests using memory filesystem

## Technical Approach

### Architecture

The feature integrates into the existing litestar-vite architecture:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ViteConfig    │────▶│  DeployConfig    │────▶│  fsspec         │
│  (existing)     │     │  (new)           │     │  filesystem     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│   CLI: deploy   │────▶│  ViteDeployer    │
│  (new command)  │     │  (sync logic)    │
└─────────────────┘     └──────────────────┘
```

### Configuration Model

```python
@dataclass
class DeployConfig:
    """CDN deployment configuration.

    Attributes:
        enabled: Enable deployment functionality.
        storage_backend: fsspec URL (e.g., "s3://bucket/assets", "gcs://bucket/path").
        storage_options: Additional options passed to fsspec (credentials, etc.).
        delete_orphaned: Remove files from remote that aren't in the new build.
        include_manifest: Include manifest.json in the deployment.
        content_types: Custom content-type mappings by extension.
    """
    enabled: bool = False
    storage_backend: str | None = None
    storage_options: dict[str, object] = field(default_factory=dict)
    delete_orphaned: bool = True
    include_manifest: bool = True
    content_types: dict[str, str] = field(default_factory=lambda: {
        ".js": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".woff2": "font/woff2",
    })
```

### Integration with ViteConfig

```python
@dataclass
class ViteConfig:
    # ... existing fields ...
    deploy: Union[DeployConfig, bool] = False

    # Existing field - used for CDN base URL
    base_url: Optional[str] = field(default_factory=lambda: os.getenv("VITE_BASE_URL"))
```

### CLI Command

```bash
# Basic usage - deploy to configured storage
litestar assets deploy

# Override storage backend
litestar assets deploy --storage s3://my-bucket/assets

# Pass storage options (credentials, region, etc.)
litestar assets deploy --storage-option key=value --storage-option region=us-east-1

# Preview without making changes
litestar assets deploy --dry-run

# Deploy existing build (skip npm run build)
litestar assets deploy --no-build

# Keep orphaned files on remote
litestar assets deploy --no-delete

# Verbose output
litestar assets deploy --verbose
```

### Sync Algorithm

1. **Build Phase** (unless `--no-build`):
   ```python
   # Set VITE_BASE_URL for the build
   os.environ["VITE_BASE_URL"] = config.base_url
   executor.execute(config.build_command, cwd=root_dir)
   ```

2. **Inventory Phase**:
   ```python
   # Local: Read manifest.json and walk bundle_dir
   local_files = collect_local_files(bundle_dir, manifest)

   # Remote: List files via fsspec
   remote_files = collect_remote_files(fs, storage_path)
   ```

3. **Diff Phase**:
   ```python
   to_upload = []
   for path, info in local_files.items():
       if path not in remote_files:
           to_upload.append(path)
       elif local_files[path].size != remote_files[path].size:
           to_upload.append(path)

   to_delete = []
   if delete_orphaned:
       for path in remote_files:
           if path not in local_files:
               to_delete.append(path)
   ```

4. **Sync Phase**:
   ```python
   # Upload new/modified files first (safer)
   for path in to_upload:
       fs.put(local_path, remote_path)

   # Then delete orphaned files
   for path in to_delete:
       fs.rm(remote_path)
   ```

### Affected Files

| File | Changes |
|------|---------|
| `src/py/litestar_vite/deploy.py` | **New**: DeployConfig, ViteDeployer, sync logic |
| `src/py/litestar_vite/config.py` | Add `deploy` field to ViteConfig |
| `src/py/litestar_vite/cli.py` | Add `vite_deploy` command |
| `src/py/litestar_vite/__init__.py` | Export DeployConfig |
| `src/py/tests/unit/test_deploy.py` | **New**: Unit tests for deploy functionality |

### API Changes

#### New Public API

```python
from litestar_vite import ViteConfig, DeployConfig

# Enable deployment with defaults
config = ViteConfig(
    deploy=True,  # Uses DeployConfig defaults
    base_url="https://cdn.example.com/assets/",
)

# Full configuration
config = ViteConfig(
    base_url="https://cdn.example.com/assets/",
    deploy=DeployConfig(
        enabled=True,
        storage_backend="s3://my-bucket/assets",
        storage_options={
            "key": os.getenv("AWS_ACCESS_KEY_ID"),
            "secret": os.getenv("AWS_SECRET_ACCESS_KEY"),
        },
        delete_orphaned=True,
    ),
)
```

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_BASE_URL` | CDN base URL (existing, used during build) |
| `VITE_DEPLOY_STORAGE` | Default storage backend URL |
| `VITE_DEPLOY_DELETE` | Enable/disable orphan deletion ("true"/"false") |

## Testing Strategy

### Unit Tests

1. **DeployConfig Tests**:
   - Default values
   - Bool shortcut (`deploy=True`)
   - Environment variable fallbacks

2. **ViteDeployer Tests**:
   - `collect_local_files()` with various directory structures
   - `compute_diff()` with upload/delete scenarios
   - Content-type detection
   - Dry-run mode (no actual changes)

3. **CLI Tests**:
   - Command parsing with all options
   - Error handling for missing config
   - Integration with VitePlugin

### Integration Tests

Using fsspec's `MemoryFileSystem`:

```python
def test_full_deploy_workflow():
    fs = MemoryFileSystem()
    deployer = ViteDeployer(config, fs)

    # Simulate build output
    (bundle_dir / "assets/main.abc123.js").write_text("...")
    (bundle_dir / "manifest.json").write_text("...")

    # Deploy
    result = deployer.sync()

    # Verify files were uploaded
    assert fs.exists("assets/main.abc123.js")
    assert fs.exists("manifest.json")
```

### Edge Cases

- Empty bundle directory
- No manifest.json
- Network failures mid-sync
- Permission errors on remote storage
- Very large files
- Unicode filenames

## Research Questions

- [x] How does Vite's manifest.json structure relate to built assets?
  - manifest.json maps source files to hashed output files
- [x] What fsspec methods are needed for upload/delete?
  - `put()`, `ls()`, `rm()`, `exists()`
- [ ] Should we support parallel uploads for performance?
  - Could use fsspec's async methods if needed

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accidental deletion of production assets | High | Dry-run mode enabled by default in CI |
| Network failure during sync | Medium | Upload new files before deleting old ones |
| Missing fsspec provider dependencies | Low | Clear error messages with install commands |
| Large file uploads timing out | Medium | Use fsspec's chunked upload support |
| Incorrect content-type headers | Low | Configurable content-type mappings |

## Example Usage

### Basic S3 Deployment

```python
# app.py
from litestar_vite import ViteConfig, VitePlugin, DeployConfig

vite = VitePlugin(
    config=ViteConfig(
        base_url="https://cdn.example.com/static/",
        deploy=DeployConfig(
            enabled=True,
            storage_backend="s3://my-bucket/static",
        ),
    )
)
```

```bash
# Deploy (AWS credentials from environment)
AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=yyy litestar assets deploy
```

### Google Cloud Storage

```python
# app.py
import os
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, DeployConfig

vite = VitePlugin(
    config=ViteConfig(
        # CDN URL where assets will be served from
        base_url="https://storage.googleapis.com/my-bucket/assets/",

        deploy=DeployConfig(
            enabled=True,
            storage_backend="gcs://my-bucket/assets",
            storage_options={
                # Option 1: Use default credentials (recommended for GCP environments)
                "token": "cloud",

                # Option 2: Service account key file
                # "token": "/path/to/service-account.json",

                # Option 3: Explicit credentials via environment
                # "token": "google_default",  # Uses GOOGLE_APPLICATION_CREDENTIALS
            },
            delete_orphaned=True,  # Remove old assets not in new build
        ),
    )
)

app = Litestar(plugins=[vite])
```

#### GCS Authentication Options

| Method | `storage_options` | Use Case |
|--------|-------------------|----------|
| Default credentials | `{"token": "cloud"}` | GCE, Cloud Run, GKE (uses metadata server) |
| Service account file | `{"token": "/path/to/key.json"}` | CI/CD pipelines, local development |
| Environment variable | `{"token": "google_default"}` | Uses `GOOGLE_APPLICATION_CREDENTIALS` env var |
| Anonymous | `{"token": "anon"}` | Public read-only buckets |

#### GCS CLI Usage

```bash
# Deploy using config from app.py
litestar assets deploy

# Preview what would be uploaded/deleted
litestar assets deploy --dry-run

# Override storage backend via CLI
litestar assets deploy --storage gcs://other-bucket/static

# Skip build step (deploy existing build)
litestar assets deploy --no-build

# Keep old files (don't delete orphaned assets)
litestar assets deploy --no-delete
```

#### GCS Deploy Output Example

```
$ litestar assets deploy

────────────────── Starting Vite build process ──────────────────
Setting VITE_BASE_URL=https://storage.googleapis.com/my-bucket/assets/
Running: npm run build
✓ Build complete

────────────────── Deploying to GCS ──────────────────
Storage: gcs://my-bucket/assets

Scanning local files...
  Found 12 files in public/dist

Scanning remote files...
  Found 8 files in gcs://my-bucket/assets

Computing changes...
  To upload: 6 files (4 new, 2 modified)
  To delete: 2 files (orphaned)

Uploading files...
  ✓ assets/main.a1b2c3d4.js (145 KB)
  ✓ assets/main.e5f6g7h8.css (23 KB)
  ✓ assets/vendor.i9j0k1l2.js (892 KB)
  ✓ assets/logo.m3n4o5p6.svg (4 KB)
  ✓ manifest.json (2 KB)
  ✓ index.html (1 KB)

Deleting orphaned files...
  ✓ assets/main.old12345.js
  ✓ assets/main.old67890.css

────────────────── Deploy Complete ──────────────────
  Uploaded: 6 files (1.1 MB)
  Deleted:  2 files
  Duration: 4.2s
```

#### GCS Requirements

```bash
# Install the GCS fsspec backend
pip install gcsfs

# Or add to your project dependencies
# pyproject.toml: dependencies = ["litestar-vite", "gcsfs"]
```

### Azure Blob Storage

```python
deploy=DeployConfig(
    enabled=True,
    storage_backend="abfs://container@account.dfs.core.windows.net/assets",
    storage_options={"account_key": os.getenv("AZURE_STORAGE_KEY")},
)
```

### SFTP/SSH

```python
deploy=DeployConfig(
    enabled=True,
    storage_backend="sftp://cdn.example.com/var/www/static",
    storage_options={
        "username": "deploy",
        "key_filename": "/path/to/key",
    },
)
```

## References

- [Django collectstatic documentation](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/)
- [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/)
- [Litestar static files documentation](https://docs.litestar.dev/latest/usage/static-files)
- [Vite base configuration](https://vitejs.dev/config/shared-options.html#base)
