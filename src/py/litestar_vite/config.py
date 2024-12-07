from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ("ViteConfig",)
TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}


@dataclass
class ViteConfig:
    """Configuration for ViteJS support.

    To enable Vite integration, pass an instance of this class to the
    :class:`Litestar <litestar.app.Litestar>` constructor using the
    'plugins' key.
    """

    bundle_dir: Path | str = field(default="public")
    """Location of the compiled assets from  Vite.

    The manifest file will also be found here.
    """
    resource_dir: Path | str = field(default="resources")
    """The directory where all typescript/javascript source are written.

    In a standalone Vue or React application, this would be equivalent to the ``./src`` directory.
    """
    public_dir: Path | str = field(default="public")
    """The optional public directory Vite serves assets from.

    In a standalone Vue or React application, this would be equivalent to the ``./public`` directory.
    """
    manifest_name: str = "manifest.json"
    """Name of the manifest file."""
    hot_file: str = "hot"
    """Name of the hot file.

    This file contains a single line containing the host, protocol, and port the Vite server is running.
    """
    hot_reload: bool = field(
        default_factory=lambda: os.getenv("VITE_HOT_RELOAD", "True") in TRUE_VALUES,
    )
    """Enable HMR for Vite development server."""
    ssr_enabled: bool = False
    """Enable SSR."""
    ssr_output_dir: Path | str | None = None
    """SSR Output path"""
    root_dir: Path | str | None = None
    """The is the base path to your application.

   In a standalone Vue or React application, this would be equivalent to the top-level project folder containing the ``./src`` directory.

    """
    is_react: bool = False
    """Enable React components."""
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    """Base URL to generate for static asset references.

    This URL will be prepended to anything generated from Vite.
    """
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "localhost"))
    """Default host to use for Vite server."""
    protocol: str = "http"
    """Protocol to use for communication"""
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    """Default port to use for Vite server."""
    run_command: list[str] = field(default_factory=lambda: ["npm", "run", "dev"])
    """Default command to use for running Vite."""
    build_watch_command: list[str] = field(default_factory=lambda: ["npm", "run", "watch"])
    """Default command to use for dev building with Vite."""
    build_command: list[str] = field(default_factory=lambda: ["npm", "run", "build"])
    """Default command to use for building with Vite."""
    install_command: list[str] = field(default_factory=lambda: ["npm", "install"])
    """Default command to use for installing Vite."""
    use_server_lifespan: bool = field(
        default_factory=lambda: os.getenv("VITE_USE_SERVER_LIFESPAN", "False") in TRUE_VALUES,
    )
    """Utilize the server lifespan hook to run Vite."""
    dev_mode: bool = field(
        default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES,
    )
    """When True, Vite will run with HMR or watch build"""
    detect_nodeenv: bool = True
    """When True, The initializer will install and configure nodeenv if present"""
    set_environment: bool = True
    """When True, configuration in this class will be set into environment variables.

    This can be useful to ensure Vite always uses the configuration supplied to the plugin
    """
    set_static_folders: bool = True
    """When True, Litestar will automatically serve assets at the `ASSET_URL` path.
    """

    def __post_init__(self) -> None:
        """Ensure that directory is set if engine is a class."""
        if self.root_dir is not None and isinstance(self.root_dir, str):
            self.root_dir = Path(self.root_dir)
        elif self.root_dir is None:
            self.root_dir = Path()
        if self.public_dir and isinstance(self.public_dir, str):
            self.public_dir = Path(self.public_dir)
        if isinstance(self.resource_dir, str):
            self.resource_dir = Path(self.resource_dir)
        if isinstance(self.bundle_dir, str):
            self.bundle_dir = Path(self.bundle_dir)
        if isinstance(self.ssr_output_dir, str):
            self.ssr_output_dir = Path(self.ssr_output_dir)
