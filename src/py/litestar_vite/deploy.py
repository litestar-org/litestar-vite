"""Vite CDN deployment utilities.

Provides a deployer for publishing built Vite assets to any fsspec backend.
DeployConfig is defined in litestar_vite.config and passed into ViteDeployer.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingTypeStubs=false

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from litestar.exceptions import SerializationException
from litestar.serialization import decode_json

from litestar_vite.config import FSSPEC_INSTALLED
from litestar_vite.config import DeployConfig as _DeployConfig
from litestar_vite.exceptions import MissingDependencyError
from litestar_vite.plugin._static import build_blocked_static_paths, is_blocked_static_metadata_path

__all__ = ("FileInfo", "SyncPlan", "SyncResult", "ViteDeployer", "format_bytes")

AbstractFileSystem = Any

_S3_SCHEMES: frozenset[str] = frozenset({"s3", "s3a"})
"""Storage backend URL schemes that interact with S3-compatible APIs.

boto3 and s3fs require the PascalCase 'ContentType' parameter, whereas GCS (gcsfs)
and Azure (adlfs) expect the lowercase 'content_type' parameter.
"""


def _suggest_install_package(storage_backend: "str | None") -> str:
    """Suggest the PyPI package to install based on backend scheme.

    Args:
        storage_backend: The storage backend URL.

    Returns:
        Suggested package to install.
    """
    if not storage_backend:
        return "fsspec"
    scheme = storage_backend.split("://", 1)[0]
    mapping = {"gcs": "gcsfs", "s3": "s3fs", "abfs": "adlfs", "az": "adlfs", "sftp": "fsspec", "ftp": "fsspec"}
    return mapping.get(scheme, "fsspec")


def _import_fsspec(storage_backend: "str | None") -> tuple[Any, Callable[..., tuple[Any, Any]]]:
    """Import fsspec lazily with a helpful error when missing.

    Args:
        storage_backend: The storage backend URL for error messaging.

    Returns:
        Tuple of fsspec module and url_to_fs function.

    Raises:
        MissingDependencyError: If fsspec is not installed.
    """
    if not FSSPEC_INSTALLED:
        raise MissingDependencyError(package=_suggest_install_package(storage_backend))

    fsspec = importlib.import_module("fsspec")
    url_to_fs = importlib.import_module("fsspec.core").url_to_fs

    return fsspec, url_to_fs


@dataclass
class FileInfo:
    """Lightweight file metadata used for CDN deployment sync planning."""

    path: str
    """Relative file path within the bundle or remote storage directory."""
    size: int
    """File size in bytes."""
    mtime: float
    """Last-modified POSIX timestamp in seconds."""


@dataclass
class SyncPlan:
    """Computed differential upload and deletion plan for CDN deployment."""

    to_upload: list[str]
    """Relative paths of local bundle files scheduled for upload."""
    to_delete: list[str]
    """Relative paths of orphaned remote files scheduled for deletion."""


@dataclass
class SyncResult:
    """Summary of a completed or dry-run CDN deployment synchronization."""

    uploaded: list[str]
    """Relative paths of files uploaded to remote storage."""
    deleted: list[str]
    """Relative paths of orphaned files removed from remote storage."""
    uploaded_bytes: int
    """Total bytes uploaded across all transferred files."""
    deleted_bytes: int
    """Total bytes reclaimed from deleted remote files."""
    dry_run: bool
    """Whether the synchronization ran in dry-run preview mode without mutating storage."""


class ViteDeployer:
    """Deploy built Vite assets to a remote fsspec backend."""

    def __init__(
        self,
        *,
        bundle_dir: Path,
        manifest_name: str,
        deploy_config: _DeployConfig,
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

        if not bundle_dir.exists():
            msg = f"Bundle directory '{bundle_dir}' does not exist. Run 'litestar assets build' before deploying."
            raise FileNotFoundError(msg)
        if not bundle_dir.is_dir():
            msg = f"Bundle path '{bundle_dir}' is not a directory."
            raise NotADirectoryError(msg)

        self.bundle_dir = bundle_dir
        self._resolved_bundle_dir = bundle_dir.resolve()
        self._manifest_name = manifest_name
        self._blocked_paths = build_blocked_static_paths(manifest_name=manifest_name)
        manifest_rel = Path(manifest_name)
        manifest_path = bundle_dir / manifest_rel
        if (
            not manifest_path.exists()
            and not manifest_rel.is_absolute()
            and (not manifest_rel.parts or manifest_rel.parts[0] != ".vite")
        ):
            vite_manifest = bundle_dir / ".vite" / manifest_rel
            if vite_manifest.exists():
                manifest_path = vite_manifest

        self.manifest_path = manifest_path
        self.config = deploy_config
        self._fs, self.remote_path = self._init_filesystem(fs, remote_path)
        self._manifest_signature: "tuple[int, int] | None" = None
        self._manifest_paths_cache: set[str] = set()

    @property
    def fs(self) -> "AbstractFileSystem":
        """Filesystem for deployment operations.

        Returns:
            The filesystem used for deployment operations.
        """
        return self._fs

    def _resolve_contained_path(self, candidate: Path, *, source_label: str) -> tuple[Path, str]:
        """Resolve ``candidate`` and enforce containment within ``bundle_dir``.

        Args:
            candidate: Filesystem path to resolve against the bundle directory.
            source_label: Raw manifest entry or filename used in error diagnostics.

        Returns:
            Tuple of resolved path and POSIX path relative to the resolved bundle directory.

        Raises:
            ValueError: If the resolved path falls outside ``bundle_dir``.
        """
        resolved = candidate.resolve()
        try:
            rel = resolved.relative_to(self._resolved_bundle_dir)
        except ValueError as exc:
            msg = f"Manifest entry {source_label!r} resolves outside bundle directory '{self.bundle_dir}'."
            raise ValueError(msg) from exc
        return resolved, rel.as_posix()

    def _is_within_bundle(self, candidate: Path) -> bool:
        """Return whether ``candidate`` resolves inside the bundle directory.

        Args:
            candidate: Filesystem path to validate.

        Returns:
            ``True`` when ``candidate`` resolves inside ``bundle_dir``, ``False`` otherwise.
        """
        try:
            candidate.resolve().relative_to(self._resolved_bundle_dir)
        except (ValueError, OSError, RuntimeError):
            return False
        return True

    def _is_excluded_deploy_path(self, rel_posix: str) -> bool:
        """Return whether ``rel_posix`` is blocked from default deployment uploads.

        Args:
            rel_posix: Bundle-relative POSIX path to check.

        Returns:
            ``True`` when the path targets blocked metadata, dotfiles, or disabled source maps.
        """
        if is_blocked_static_metadata_path(rel_posix, self._blocked_paths):
            return True
        return not self.config.include_sourcemaps and rel_posix.lower().endswith(".map")

    def _normalize_manifest_entry(self, raw_entry: str) -> str:
        """Validate a raw manifest entry before resolving it within the bundle directory.

        Args:
            raw_entry: Raw path string extracted from the Vite manifest.

        Returns:
            Normalized bundle-relative POSIX path string.

        Raises:
            ValueError: If the entry uses backslashes, double slashes, empty segments, or ``..``.
        """
        if "\\" in raw_entry or raw_entry.startswith("//"):
            msg = f"Manifest entry {raw_entry!r} resolves outside bundle directory '{self.bundle_dir}'."
            raise ValueError(msg)
        rel_entry = raw_entry.removeprefix("/")
        if not rel_entry or Path(rel_entry).is_absolute() or any(part in {"", ".."} for part in rel_entry.split("/")):
            msg = f"Manifest entry {raw_entry!r} resolves outside bundle directory '{self.bundle_dir}'."
            raise ValueError(msg)
        return rel_entry

    def _collect_manifest_entries(self, manifest_paths: set[str], files: dict[str, FileInfo]) -> None:
        """Resolve and collect manifest-referenced assets and optional source maps.

        Args:
            manifest_paths: Raw path entries extracted from the Vite manifest.
            files: Dictionary mapping bundle-relative paths to file metadata to populate.
        """
        for raw_entry in manifest_paths:
            rel_entry = self._normalize_manifest_entry(raw_entry)
            resolved, rel_posix = self._resolve_contained_path(
                self._resolved_bundle_dir / rel_entry, source_label=raw_entry
            )
            if (
                resolved.is_file()
                and not self._is_excluded_deploy_path(rel_entry)
                and not self._is_excluded_deploy_path(rel_posix)
            ):
                stat = resolved.stat()
                files[rel_posix] = FileInfo(path=rel_posix, size=stat.st_size, mtime=stat.st_mtime)

            if self.config.include_sourcemaps:
                map_rel_entry = f"{rel_entry}.map"
                map_candidate = self._resolved_bundle_dir / map_rel_entry
                if map_candidate.exists() and map_candidate.is_file():
                    map_resolved, map_rel_posix = self._resolve_contained_path(
                        map_candidate, source_label=f"{raw_entry}.map"
                    )
                    if not is_blocked_static_metadata_path(
                        map_rel_entry, self._blocked_paths
                    ) and not is_blocked_static_metadata_path(map_rel_posix, self._blocked_paths):
                        map_stat = map_resolved.stat()
                        files[map_rel_posix] = FileInfo(
                            path=map_rel_posix, size=map_stat.st_size, mtime=map_stat.st_mtime
                        )

    def collect_local_files(self) -> dict[str, FileInfo]:
        """Collect local files to publish.

        Returns:
            Mapping of relative paths to file metadata.

        Raises:
            ValueError: If a manifest entry or explicit manifest resolves outside ``bundle_dir``.
        """
        manifest_paths = self._get_manifest_paths()
        files: dict[str, FileInfo] = {}

        if manifest_paths:
            self._collect_manifest_entries(manifest_paths, files)
            self._index_unmanaged_files(manifest_paths, files)
        else:
            for path in self.bundle_dir.rglob("*"):
                if path.is_dir() or not path.exists() or not self._is_within_bundle(path):
                    continue
                rel_posix = path.relative_to(self.bundle_dir).as_posix()
                resolved_rel = path.resolve().relative_to(self._resolved_bundle_dir).as_posix()
                if self._is_excluded_deploy_path(rel_posix) or self._is_excluded_deploy_path(resolved_rel):
                    continue
                stat = path.stat()
                files[rel_posix] = FileInfo(path=rel_posix, size=stat.st_size, mtime=stat.st_mtime)

        if self.config.include_manifest and self.manifest_path.exists() and self.manifest_path.is_file():
            manifest_resolved, manifest_rel = self._resolve_contained_path(
                self.manifest_path, source_label=self._manifest_name
            )
            stat = manifest_resolved.stat()
            files[manifest_rel] = FileInfo(path=manifest_rel, size=stat.st_size, mtime=stat.st_mtime)

        index_html = self.bundle_dir / "index.html"
        if index_html.is_file() and self._is_within_bundle(index_html):
            resolved_index_rel = index_html.resolve().relative_to(self._resolved_bundle_dir).as_posix()
            if not self._is_excluded_deploy_path(resolved_index_rel):
                stat = index_html.stat()
                files.setdefault("index.html", FileInfo(path="index.html", size=stat.st_size, mtime=stat.st_mtime))

        return files

    def _index_unmanaged_files(self, manifest_paths: set[str], files: dict[str, FileInfo]) -> None:
        """Index Vite public passthrough assets that are absent from the manifest.

        Vite copies the contents of ``public/`` into the build output directory
        verbatim without recording them in ``manifest.json``. When deploy sync operates
        with ``delete_orphaned=True``, any local bundle file missing from the local
        index is considered an orphan remotely and purged. To prevent deleting public
        assets (such as ``favicon.ico``, ``robots.txt``, and static images) while still
        excluding stale hashed build artifacts, this helper computes the top-level
        directories managed by the manifest (e.g. ``assets/`` and ``.vite/``) and
        indexes all non-directory files outside those directories.

        Args:
            manifest_paths: Relative file paths referenced by the Vite manifest.
            files: Dictionary mapping relative paths to FileInfo objects to populate.
        """
        managed_dirs: set[str] = {".vite"}
        for p in manifest_paths:
            parts = Path(p.removeprefix("/")).parts
            if len(parts) > 1:
                managed_dirs.add(parts[0])

        for path in self.bundle_dir.rglob("*"):
            if path.is_dir() or not path.exists() or not self._is_within_bundle(path):
                continue
            rel = path.relative_to(self.bundle_dir)
            if rel.parts and rel.parts[0] in managed_dirs:
                continue
            rel_posix = rel.as_posix()
            resolved_rel = path.resolve().relative_to(self._resolved_bundle_dir).as_posix()
            if self._is_excluded_deploy_path(rel_posix) or self._is_excluded_deploy_path(resolved_rel):
                continue
            stat = path.stat()
            files.setdefault(rel_posix, FileInfo(path=rel_posix, size=stat.st_size, mtime=stat.st_mtime))

    def _get_manifest_paths(self) -> set[str]:
        """Get manifest paths from cache when possible.

        Returns:
            File paths referenced by manifest.json.
        """
        if not self.manifest_path.exists():
            self._manifest_signature = None
            self._manifest_paths_cache = set[str]()
            return set[str]()

        stat = self.manifest_path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        if self._manifest_signature == signature:
            return set(self._manifest_paths_cache)

        manifest_paths = self._paths_from_manifest(self.manifest_path)
        self._manifest_paths_cache = manifest_paths
        self._manifest_signature = signature
        return set(manifest_paths)

    def collect_remote_files(self) -> dict[str, FileInfo]:
        """Collect remote files from the target storage.

        Returns:
            Mapping of relative remote paths to file metadata.
        """
        remote_files: dict[str, FileInfo] = {}
        base = self.remote_path.rstrip("/")
        for entry in self._iter_remote_entries(self.remote_path):
            name = entry.get("name")
            if name is None:
                continue
            rel_path = self._relative_remote_path(name, base)
            raw_size = entry.get("size")
            size = int(raw_size) if raw_size is not None else 0
            raw_mtime = entry.get("mtime") or entry.get("LastModified")
            if raw_mtime is not None and hasattr(raw_mtime, "timestamp"):
                mtime = float(raw_mtime.timestamp())
            elif raw_mtime is not None:
                try:
                    mtime = float(raw_mtime)
                except (ValueError, TypeError):
                    mtime = 0.0
            else:
                mtime = 0.0
            remote_files[rel_path] = FileInfo(path=rel_path, size=size, mtime=mtime)
        return remote_files

    def _iter_remote_entries(self, root: str) -> "Iterable[dict[str, Any]]":
        """Yield remote file entries recursively from ``root``."""
        try:
            entries = cast("list[dict[str, Any]]", self.fs.ls(root, detail=True))
        except (FileNotFoundError, OSError):
            return

        for entry in entries:
            name = entry.get("name")
            if name is None:
                continue
            if entry.get("type") == "directory":
                yield from self._iter_remote_entries(str(name))
                continue
            yield entry

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

    def sync(self, *, dry_run: bool = False, on_progress: Callable[[str, str], None] | None = None) -> SyncResult:
        """Sync local bundle to remote storage.

        Uploads modified or missing local assets and removes remote orphaned assets
        when configured. S3-compatible backends (s3, s3a) receive the PascalCase
        'ContentType' parameter required by boto3, while other backends (such as GCS
        or Azure Blob Storage) receive the lowercase 'content_type' parameter.

        Args:
            dry_run: When True, compute the plan without uploading or deleting.
            on_progress: Optional callback receiving an action and path for each step.

        Returns:
            SyncResult summarizing the deployment.
        """

        local_files = self.collect_local_files()
        remote_files = self.collect_remote_files()

        if not local_files and remote_files and self.config.delete_orphaned:
            msg = (
                f"Cannot sync bundle: local bundle directory '{self.bundle_dir}' produced 0 deployable files. "
                "Aborting to prevent accidental deletion of all remote assets."
            )
            raise ValueError(msg)

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
            put_kwargs: dict[str, Any] = {}
            if content_type:
                scheme = (self.config.storage_backend or "").split("://", 1)[0].lower()
                if scheme in _S3_SCHEMES:
                    put_kwargs["ContentType"] = content_type
                else:
                    put_kwargs["content_type"] = content_type
            self.fs.put(local_path.as_posix(), remote_path, **put_kwargs)
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

    def _init_filesystem(
        self, fs: "AbstractFileSystem | None", remote_path: str | None
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
        """Extract file paths referenced by manifest.json.

        Returns:
            Set of file paths.
        """

        try:
            manifest_data: Any = decode_json(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SerializationException):
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
        """Compute remote path relative to deployment root.

        Returns:
            The remote path relative to the deployment root.
        """

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
        """Join remote base and relative path.

        Returns:
            The full remote path.
        """

        if not self.remote_path:
            return relative_path
        return f"{self.remote_path.rstrip('/')}/{relative_path.lstrip('/')}"


def format_bytes(size: int) -> str:
    """Human friendly byte formatting.

    Returns:
        The formatted byte size string.
    """

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
