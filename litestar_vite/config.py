from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from inspect import isclass
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from litestar.exceptions import ImproperlyConfiguredException
from litestar.template import TemplateEngineProtocol

__all__ = ["ViteConfig", "ViteTemplateConfig"]


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from litestar.types import PathType

    from litestar_vite.template_engine import ViteTemplateEngine

T = TypeVar("T", bound=TemplateEngineProtocol)


@dataclass
class ViteConfig:
    """Configuration for ViteJS support.

    To enable Vite integration, pass an instance of this class to the
    :class:`Litestar <litestar.app.Litestar>` constructor using the
    'plugins' key.
    """

    bundle_dir: Path
    """Location of the compiled assets from  Vite.

    The manifest file will also be found here.
    """
    resource_dir: Path
    """The directory where all typescript/javascript source are written.

    In a standalone Vue or React application, this would be equivalent to the ``./src`` directory.
    """
    assets_dir: Path
    """These are the assets that Vite will serve when developing.

    This should include any images, CSS, or other media referenced.

    These will be included in the bundle directory on build.
    """
    templates_dir: Path
    """Location of the Jinja2 template file.
    """
    manifest_name: str = ".vite/manifest.json"
    """Name of the manifest file."""
    hot_file: str = "hot"
    """Name of the hot file.

    This file contains a single line containing the host, protocol, and port the Vite server is running.
    """
    hot_reload: bool = False
    """Enable HMR for Vite development server."""
    ssr_enabled: bool = False
    """Enable SSR."""
    ssr_output_dir: Path | None = None
    """SSR Output path"""
    root_dir: Path | None = None
    """The is the base path to your application.

   In a standalone Vue or React application, this would be equivalent to the ``./src`` directory.

    """
    is_react: bool = False
    """Enable React components."""
    asset_url: str = "/static/"
    """Base URL to generate for static asset references.

    This URL will be prepended to anything generated from Vite.
    """
    host: str = "localhost"
    """Default host to use for Vite server."""
    protocol: str = "http"
    """Protocol to use for communication"""
    port: int = 5173
    """Default port to use for Vite server."""
    run_command: list[str] = field(default_factory=lambda: ["npm", "run", "dev"])
    """Default command to use for running Vite."""
    build_watch_command: list[str] = field(default_factory=lambda: ["npm", "run", "build", "--watch"])
    """Default command to use for dev building with Vite."""
    build_command: list[str] = field(default_factory=lambda: ["npm", "run", "build"])
    """Default command to use for building with Vite."""
    install_command: list[str] = field(default_factory=lambda: ["npm", "install"])
    """Default command to use for installing Vite."""
    use_server_lifespan: bool = False
    """Utilize the server lifespan hook to run Vite."""
    dev_mode: bool = False
    """When True, Vite will run with HMR or watch build"""


@dataclass
class ViteTemplateConfig(Generic[T]):
    """Configuration for Templating.

    To enable templating, pass an instance of this class to the
    :class:`Litestar <litestar.app.Litestar>` constructor using the
    'template_config' key.
    """

    engine: type[ViteTemplateEngine]
    """A template engine adhering to the :class:`TemplateEngineProtocol
    <litestar.template.base.TemplateEngineProtocol>`."""
    config: ViteConfig
    """A a config for the vite engine`."""
    directory: PathType | None = field(default=None)
    """A directory or list of directories from which to serve templates."""
    engine_callback: Callable[[T], None] | None = field(default=None)
    """A callback function that allows modifying the instantiated templating
    protocol."""

    def __post_init__(self) -> None:
        """Ensure that directory is set if engine is a class."""
        if isclass(self.engine) and not self.directory:
            msg = "directory is a required kwarg when passing a template engine class"
            raise ImproperlyConfiguredException(msg)

    def to_engine(self) -> T:
        """Instantiate the template engine."""
        template_engine = cast(
            "T",
            self.engine(directory=self.directory, config=self.config) if isclass(self.engine) else self.engine,
        )
        if callable(self.engine_callback):
            self.engine_callback(template_engine)
        return template_engine

    @cached_property
    def engine_instance(self) -> T:
        """Return the template engine instance."""
        return self.to_engine()
