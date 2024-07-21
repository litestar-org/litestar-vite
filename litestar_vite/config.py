from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from inspect import isclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

from litestar.exceptions import ImproperlyConfiguredException
from litestar.template import TemplateConfig, TemplateEngineProtocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.types import PathType

__all__ = ("ViteConfig", "ViteTemplateConfig")
EngineType = TypeVar("EngineType", bound=TemplateEngineProtocol[Any, Any])
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
    template_dir: Path | str | None = field(default="templates")
    """Location of the Jinja2 template file."""
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
        if self.template_dir is not None and isinstance(self.template_dir, str):
            self.template_dir = Path(self.template_dir)
        if self.public_dir and isinstance(self.public_dir, str):
            self.public_dir = Path(self.public_dir)
        if isinstance(self.resource_dir, str):
            self.resource_dir = Path(self.resource_dir)
        if isinstance(self.bundle_dir, str):
            self.bundle_dir = Path(self.bundle_dir)
        if isinstance(self.ssr_output_dir, str):
            self.ssr_output_dir = Path(self.ssr_output_dir)


@dataclass
class ViteTemplateConfig(TemplateConfig[EngineType]):
    """Configuration for Templating.

    To enable templating, pass an instance of this class to the
    :class:`Litestar <litestar.app.Litestar>` constructor using the
    'template_config' key.
    """

    config: ViteConfig = field(default_factory=lambda: ViteConfig())
    """A a config for the vite engine`."""
    engine: type[EngineType] | EngineType | None = field(default=None)
    """A template engine adhering to the :class:`TemplateEngineProtocol
    <litestar.template.base.TemplateEngineProtocol>`."""
    directory: PathType | list[PathType] | None = field(default=None)
    """A directory or list of directories from which to serve templates."""
    engine_callback: Callable[[EngineType], None] | None = field(default=None)
    """A callback function that allows modifying the instantiated templating
    protocol."""

    instance: EngineType | None = field(default=None)
    """An instance of the templating protocol."""

    def __post_init__(self) -> None:
        """Ensure that directory is set if engine is a class."""
        if isclass(self.engine) and not self.directory:  # pyright: ignore[reportUnknownMemberType]
            msg = "directory is a required kwarg when passing a template engine class"
            raise ImproperlyConfiguredException(msg)
        """Ensure that directory is not set if instance is."""
        if self.instance is not None and self.directory is not None:  # pyright: ignore[reportUnknownMemberType]
            msg = "directory cannot be set if instance is"
            raise ImproperlyConfiguredException(msg)

    def to_engine(self) -> EngineType:
        """Instantiate the template engine."""
        template_engine = cast(
            "EngineType",
            self.engine(directory=self.directory, config=self.config, engine_instance=None)  # pyright: ignore[reportUnknownMemberType,reportCallIssue]
            if isclass(self.engine)
            else self.engine,
        )
        if callable(self.engine_callback):
            self.engine_callback(template_engine)
        return template_engine

    @cached_property
    def engine_instance(self) -> EngineType:
        """Return the template engine instance."""
        return self.to_engine() if self.instance is None else self.instance
