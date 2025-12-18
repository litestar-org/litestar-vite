"""CDN deployment configuration."""

import os
from dataclasses import dataclass, field, replace
from typing import Any

from litestar_vite.config._constants import TRUE_VALUES, default_content_types, default_storage_options

__all__ = ("DeployConfig",)


@dataclass
class DeployConfig:
    """CDN deployment configuration.

    Attributes:
        enabled: Enable deployment features.
        storage_backend: fsspec URL for the target location (e.g., ``gcs://bucket/path``).
        storage_options: Provider options forwarded to ``fsspec`` (credentials, region, etc.).
        asset_url: Public URL prefix where deployed assets will be served (e.g., ``https://cdn.example.com/assets/``).
            When set and deployment is enabled, this value is written to ``.litestar.json`` as ``deployAssetUrl`` and
            used by the Vite plugin as the ``base`` during ``vite build``. It does not replace ``PathConfig.asset_url``.
        delete_orphaned: Remove remote files not present in the local bundle.
        include_manifest: Upload ``manifest.json`` alongside assets.
        content_types: Optional content-type overrides keyed by file extension.
    """

    enabled: bool = True
    storage_backend: "str | None" = field(default_factory=lambda: os.getenv("VITE_DEPLOY_STORAGE"))
    storage_options: dict[str, Any] = field(default_factory=default_storage_options)
    asset_url: "str | None" = field(default_factory=lambda: os.getenv("VITE_DEPLOY_ASSET_URL"))
    delete_orphaned: bool = field(default_factory=lambda: os.getenv("VITE_DEPLOY_DELETE", "true") in TRUE_VALUES)
    include_manifest: bool = True
    content_types: dict[str, str] = field(default_factory=default_content_types)

    def __post_init__(self) -> None:
        """Apply environment fallbacks."""
        if self.storage_backend is None:
            self.storage_backend = os.getenv("VITE_DEPLOY_STORAGE")
        if self.asset_url is None:
            self.asset_url = os.getenv("VITE_DEPLOY_ASSET_URL")

        if self.asset_url and self.asset_url != "/" and not self.asset_url.endswith("/"):
            self.asset_url = f"{self.asset_url}/"

    def with_overrides(
        self,
        storage_backend: "str | None" = None,
        storage_options: "dict[str, Any] | None" = None,
        asset_url: "str | None" = None,
        delete_orphaned: "bool | None" = None,
    ) -> "DeployConfig":
        """Return a copy with overrides applied.

        Args:
            storage_backend: Override for the storage URL.
            storage_options: Override for backend options.
            asset_url: Override for the public asset URL.
            delete_orphaned: Override deletion behaviour.

        Returns:
            DeployConfig copy with updated fields.
        """
        return replace(
            self,
            storage_backend=storage_backend or self.storage_backend,
            storage_options=storage_options or self.storage_options,
            asset_url=asset_url or self.asset_url,
            delete_orphaned=self.delete_orphaned if delete_orphaned is None else delete_orphaned,
        )
