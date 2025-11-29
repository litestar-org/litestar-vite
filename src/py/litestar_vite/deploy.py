"""Vite CDN deployment utilities."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from importlib.util import find_spec
from pathlib import Path
from typing import Any, cast

from litestar_vite.exceptions import MissingDependencyError

AbstractFileSystem = Any

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}


def _default_content_types() -> dict[str, str]:
    """Default content-type mappings keyed by file extension."""

    return {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".cjs": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
    }


def _suggest_install_extra(storage_backend: str | None) -> str:
    """Suggest an install target based on backend scheme."""

    if not storage_backend:
        return "fsspec"
    scheme = storage_backend.split("://", 1)[0]
    mapping = {
        "gcs": "gcsfs",
        "s3": "s3fs",
        "abfs": "adlfs",
        "az": "adlfs",
        "sftp": "fsspec",
        "ftp": "fsspec",
    }
    return mapping.get(scheme, "fsspec")


def _import_fsspec(storage_backend: str | None) -> tuple[Any, Callable[..., tuple[Any, Any]]]:
    """Import fsspec lazily with a helpful error when missing."""

    if find_spec("fsspec") is None:
        msg = "fsspec"
        raise MissingDependencyError(msg, install_package=_suggest_install_extra(storage_backend))

    import fsspec  # type: ignore[reportMissingTypeStubs]
    from fsspec.core import url_to_fs  # type: ignore[reportMissingTypeStubs]

    return fsspec, url_to_fs


@dataclass
class DeployConfig:
    """CDN deployment configuration.

    Attributes:
        enabled: Enable deployment features.
        storage_backend: fsspec URL for the target location (e.g., ``gcs://bucket/path``).
        storage_options: Provider options forwarded to ``fsspec`` (credentials, region, etc.).
        delete_orphaned: Remove remote files not present in the local bundle.
        include_manifest: Upload ``manifest.json`` alongside assets.
        content_types: Optional content-type overrides keyed by file extension.
    """

    enabled: bool = False
    storage_backend: str | None = field(default_factory=lambda: os.getenv("VITE_DEPLOY_STORAGE"))
    storage_options: dict[str, Any] = field(default_factory=lambda: cast("dict[str, Any]", {}))
    delete_orphaned: bool = field(default_factory=lambda: os.getenv("VITE_DEPLOY_DELETE", "true") in TRUE_VALUES)
    include_manifest: bool = True
    content_types: dict[str, str] = field(default_factory=_default_content_types)

    def __post_init__(self) -> None:
        """Apply environment fallbacks."""
        if self.storage_backend is None:
            self.storage_backend = os.getenv("VITE_DEPLOY_STORAGE")

    def with_overrides(
        self,
        storage_backend: str | None = None,
        storage_options: dict[str, Any] | None = None,
        delete_orphaned: bool | None = None,
    ) -> "DeployConfig":
        """Return a copy with overrides applied.

        Args:
            storage_backend: Override for the storage URL.
            storage_options: Override for backend options.
            delete_orphaned: Override deletion behaviour.

        Returns:
            DeployConfig copy with updated fields.
        """

        return replace(
            self,
            storage_backend=storage_backend or self.storage_backend,
            storage_options=storage_options or self.storage_options,
            delete_orphaned=self.delete_orphaned if delete_orphaned is None else delete_orphaned,
        )


@dataclass
class FileInfo:
    """Lightweight file metadata used for sync planning."""

    path: str
    size: int
    mtime: float


@dataclass
class SyncPlan:
    """Diff plan for deployment."""

    to_upload: list[str]
    to_delete: list[str]


@dataclass
class SyncResult:
    """Deployment result summary."""

    uploaded: list[str]
    deleted: list[str]
    uploaded_bytes: int
    deleted_bytes: int
    dry_run: bool


class ViteDeployer:
    """Deploy built Vite assets to a remote fsspec backend."""

    def __init__(
        self,
        *,
        bundle_dir: Path,
        manifest_name: str,
        deploy_config: DeployConfig,
        fs: "AbstractFileSystem | None" = None,
        remote_path: str | None = None,
    ) -> None:
        self._fsspec, self._url_to_fs = _import_fsspec(deploy_config.storage_backend)
        if not deploy_config.enabled:
            msg = "Deployment is disabled. Enable DeployConfig.enabled to proceed."
            raise ValueError(msg)
        if not deploy_config.storage_backend:
            msg = "DeployConfig.storage_backend is required (e.g. gcs://bucket/assets)."
            raise ValueError(msg)

        self.bundle_dir = bundle_dir
        self.manifest_path = bundle_dir / manifest_name
        self.config = deploy_config
        self._fs, self.remote_path = self._init_filesystem(fs, remote_path)

    @property
    def fs(self) -> "AbstractFileSystem":
        """Filesystem for deployment operations."""

        return self._fs

    # ------------------------------------------------------------------ #
    # Discovery helpers
    # ------------------------------------------------------------------ #
    def collect_local_files(self) -> dict[str, FileInfo]:
        """Collect local files to publish.

        Returns:
            Mapping of relative paths to file metadata.
        """

        manifest_paths: set[str] = (
            self._paths_from_manifest(self.manifest_path) if self.manifest_path.exists() else set[str]()
        )

        include_manifest = self.config.include_manifest and self.manifest_path.exists()
        files: dict[str, FileInfo] = {}

        if manifest_paths:
            candidate_paths: list[Path] = [self.bundle_dir / p for p in manifest_paths]
            if include_manifest:
                candidate_paths.append(self.manifest_path)
            candidates: Iterable[Path] = candidate_paths
        else:
            candidates = self.bundle_dir.rglob("*")

        for path in candidates:
            if path.is_dir():
                continue
            if not path.exists():
                continue
            rel_path = path.relative_to(self.bundle_dir).as_posix()
            stat = path.stat()
            files[rel_path] = FileInfo(path=rel_path, size=stat.st_size, mtime=stat.st_mtime)

        # Ensure index.html is always deployed if present
        index_html = self.bundle_dir / "index.html"
        if index_html.exists():
            stat = index_html.stat()
            files.setdefault(
                "index.html",
                FileInfo(path="index.html", size=stat.st_size, mtime=stat.st_mtime),
            )

        return files

    def collect_remote_files(self) -> dict[str, FileInfo]:
        """Collect remote files from the target storage.

        Returns:
            Mapping of relative remote paths to file metadata.
        """

        try:
            entries = cast("list[dict[str, Any]]", self.fs.ls(self.remote_path, detail=True))
        except (FileNotFoundError, OSError):
            return {}

        remote_files: dict[str, FileInfo] = {}
        base = self.remote_path.rstrip("/")
        for entry in entries:
            name = entry.get("name")
            if name is None:
                continue
            if entry.get("type") == "directory":
                continue
            rel_path = self._relative_remote_path(name, base)
            remote_files[rel_path] = FileInfo(
                path=rel_path,
                size=int(entry.get("size", 0)),
                mtime=float(entry.get("mtime", 0.0)),
            )
        return remote_files

    # ------------------------------------------------------------------ #
    # Diff & sync
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute_diff(local: dict[str, FileInfo], remote: dict[str, FileInfo], delete_orphaned: bool) -> SyncPlan:
        """Compute which files to upload or delete.

        Args:
            local: Local files keyed by relative path.
            remote: Remote files keyed by relative path.
            delete_orphaned: Whether to remove remote-only files.

        Returns:
            SyncPlan listing upload and delete actions.
        """

        to_upload: list[str] = []
        for path, info in local.items():
            remote_info = remote.get(path)
            if remote_info is None or remote_info.size != info.size:
                to_upload.append(path)

        to_delete: list[str] = [path for path in remote if path not in local] if delete_orphaned else []

        return SyncPlan(to_upload=to_upload, to_delete=to_delete)

    def sync(
        self,
        *,
        dry_run: bool = False,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> SyncResult:
        """Sync local bundle to remote storage.

        Args:
            dry_run: When True, compute the plan without uploading or deleting.
            on_progress: Optional callback receiving an action and path for each step.

        Returns:
            SyncResult summarising the deployment.
        """

        local_files = self.collect_local_files()
        remote_files = self.collect_remote_files()
        plan = self.compute_diff(local_files, remote_files, delete_orphaned=self.config.delete_orphaned)

        uploaded: list[str] = []
        deleted: list[str] = []
        uploaded_bytes = 0
        deleted_bytes = 0

        if dry_run:
            return SyncResult(
                uploaded=plan.to_upload,
                deleted=plan.to_delete,
                uploaded_bytes=sum(local_files[p].size for p in plan.to_upload),
                deleted_bytes=sum(remote_files[p].size for p in plan.to_delete),
                dry_run=True,
            )

        for path in plan.to_upload:
            local_path = self.bundle_dir / path
            remote_path = self._join_remote(path)
            content_type: str | None = self.config.content_types.get(Path(path).suffix)
            if content_type:
                self.fs.put(local_path.as_posix(), remote_path, content_type=content_type)
            else:
                self.fs.put(local_path.as_posix(), remote_path)
            uploaded.append(path)
            uploaded_bytes += local_files[path].size
            if on_progress:
                on_progress("upload", path)

        for path in plan.to_delete:
            remote_path = self._join_remote(path)
            self.fs.rm(remote_path)
            deleted.append(path)
            deleted_bytes += remote_files[path].size
            if on_progress:
                on_progress("delete", path)

        return SyncResult(
            uploaded=uploaded,
            deleted=deleted,
            uploaded_bytes=uploaded_bytes,
            deleted_bytes=deleted_bytes,
            dry_run=False,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _init_filesystem(
        self,
        fs: "AbstractFileSystem | None",
        remote_path: str | None,
    ) -> "tuple[AbstractFileSystem, str]":
        if fs is not None and remote_path is not None:
            return fs, remote_path

        if fs is not None:
            _, resolved_path = self._url_to_fs(self.config.storage_backend or "", **self.config.storage_options)
            resolved_str = str(resolved_path)
            return fs, remote_path or resolved_str

        filesystem, resolved_path = self._url_to_fs(self.config.storage_backend or "", **self.config.storage_options)
        resolved_str = str(resolved_path)
        return filesystem, remote_path or resolved_str

    def _paths_from_manifest(self, manifest_path: Path) -> set[str]:
        """Extract file paths referenced by manifest.json."""

        try:
            manifest_data: Any = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            return set[str]()

        paths: set[str] = set()
        if isinstance(manifest_data, dict):
            for value in manifest_data.values():
                if not isinstance(value, dict):
                    continue
                file_path = value.get("file")
                if isinstance(file_path, str):
                    paths.add(file_path)
                for field in ("css", "assets"):
                    for item in value.get(field, []) or []:
                        if isinstance(item, str):
                            paths.add(item)
        return paths

    def _relative_remote_path(self, full_path: str, base: str) -> str:
        """Compute remote path relative to deployment root."""

        if "://" in full_path:
            full_path = full_path.split("://", 1)[1]
        if "://" in base:
            base = base.split("://", 1)[1]
        full_path = full_path.lstrip("/")
        base = base.lstrip("/")
        if not base:
            return full_path.lstrip("/")
        cleaned = full_path.removeprefix(base)
        return cleaned.lstrip("/")

    def _join_remote(self, relative_path: str) -> str:
        """Join remote base and relative path."""

        if not self.remote_path:
            return relative_path
        return f"{self.remote_path.rstrip('/')}/{relative_path.lstrip('/')}"


def format_bytes(size: int) -> str:
    """Human friendly byte formatting."""

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
