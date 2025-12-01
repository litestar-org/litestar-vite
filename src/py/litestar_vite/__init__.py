"""Litestar-Vite: Seamless integration between Litestar and Vite.

This package provides integration between the Litestar web framework and
Vite, the next-generation frontend build tool.

Basic usage:
    from litestar import Litestar
    from litestar_vite import VitePlugin, ViteConfig

    app = Litestar(
        plugins=[VitePlugin(config=ViteConfig(dev_mode=True))],
    )

For more advanced configuration:
    from litestar_vite import VitePlugin, ViteConfig, PathConfig, RuntimeConfig

    app = Litestar(
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="spa",
                    dev_mode=True,
                    paths=PathConfig(bundle_dir=Path("dist")),
                    runtime=RuntimeConfig(executor="bun"),
                    types=True,
                )
            )
        ],
    )
"""

from litestar_vite import inertia
from litestar_vite.codegen import RouteMetadata, extract_route_metadata, generate_routes_json
from litestar_vite.config import (
    DeployConfig,
    ExternalDevServer,
    InertiaConfig,
    PathConfig,
    RuntimeConfig,
    TypeGenConfig,
    ViteConfig,
)
from litestar_vite.html_transform import HtmlTransformer
from litestar_vite.loader import ViteAssetLoader
from litestar_vite.plugin import VitePlugin
from litestar_vite.spa import ViteSPAHandler

__all__ = (
    # Config components
    "DeployConfig",
    "ExternalDevServer",
    "HtmlTransformer",
    "InertiaConfig",
    "PathConfig",
    "RouteMetadata",
    "RuntimeConfig",
    "TypeGenConfig",
    "ViteAssetLoader",
    "ViteConfig",
    # Main exports
    "VitePlugin",
    "ViteSPAHandler",
    # Codegen utilities
    "extract_route_metadata",
    "generate_routes_json",
    # Submodule
    "inertia",
)
