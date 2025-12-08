====================
CDN Deployment
====================

Deploy built Vite assets to remote storage backends using fsspec.

The ViteDeployer class provides a robust deployment solution for syncing
built assets to cloud storage providers like S3, GCS, Azure Blob Storage,
and more.

Features
--------

- Deploy to any fsspec-compatible backend (S3, GCS, Azure, etc.)
- Smart diffing: only uploads changed files
- Optional orphaned file cleanup
- Dry-run mode for testing
- Progress callbacks for monitoring
- Manifest-based file tracking
- Content-Type header configuration

Available Classes
-----------------

ViteDeployer
    Main class for deploying Vite assets to remote storage.

FileInfo
    Lightweight file metadata used for sync planning.

SyncPlan
    Diff plan showing files to upload or delete.

SyncResult
    Deployment result summary with uploaded/deleted file counts and sizes.

Available Functions
-------------------

format_bytes
    Human-friendly byte size formatting (e.g., "1.5 MB").

.. automodule:: litestar_vite.deploy
    :members:
    :show-inheritance:
