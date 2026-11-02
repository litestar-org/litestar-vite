"""Production asset serving, Granian native static placement, and CDN deployment."""

from __future__ import annotations

from pathlib import Path

from litestar import Litestar

from litestar_vite import (
    DeployConfig,
    PathConfig,
    RuntimeConfig,
    StaticPlacement,
    StaticServerConfig,
    StaticServerMount,
    ViteConfig,
)


def create_production_config(bundle_dir: Path) -> ViteConfig:
    """Build a production ``ViteConfig`` with CDN prefix and Granian static offload."""
    return ViteConfig(
        mode="spa",
        dev_mode=False,
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="https://cdn.example.com/assets/"),
        deploy=DeployConfig(
            enabled=True,
            storage_backend="s3://my-app-assets-prod/assets",
            asset_url="https://cdn.example.com/assets/",
            delete_orphaned=True,
        ),
        runtime=RuntimeConfig(start_dev_server=False),
    )


def create_static_server_config() -> StaticServerConfig:
    """Configure Granian Rust-level static file serving with native placement."""
    return StaticServerConfig(
        placement=StaticPlacement.NATIVE, mounts=(StaticServerMount(route="/static", directory=Path("public/build")),)
    )


def main() -> None:
    """Verify production ``ViteConfig`` and ``StaticServerConfig`` settings."""
    cfg = create_production_config(Path("public/build"))
    static_cfg = create_static_server_config()
    assert cfg.dev_mode is False
    assert cfg.asset_url == "https://cdn.example.com/assets/"
    assert static_cfg.placement == StaticPlacement.NATIVE
    assert Litestar is not None


__all__ = ("create_production_config", "create_static_server_config", "main")
