import os
import platform
import signal
import subprocess
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import JINJA_INSTALLED

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.datastructures import CacheControlHeader
    from litestar.openapi.spec import SecurityRequirement
    from litestar.types import (
        AfterRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        AfterResponseHookHandler,  # pyright: ignore[reportUnknownVariableType]
        BeforeRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        ExceptionHandlersMap,
        Guard,  # pyright: ignore[reportUnknownVariableType]
        Middleware,
    )

    from litestar_vite.config import ViteConfig
    from litestar_vite.loader import ViteAssetLoader


def set_environment(config: "ViteConfig") -> None:
    """Configure environment for easier integration"""
    from litestar import __version__ as litestar_version

    os.environ.setdefault("ASSET_URL", config.asset_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    os.environ.setdefault("LITESTAR_VERSION", litestar_version.formatted())
    os.environ.setdefault("APP_URL", f"http://localhost:{os.environ.get('LITESTAR_PORT', '8000')}")
    if config.dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.dev_mode))


@dataclass
class StaticFilesConfig:
    after_request: "Optional[AfterRequestHookHandler]" = None
    after_response: "Optional[AfterResponseHookHandler]" = None
    before_request: "Optional[BeforeRequestHookHandler]" = None
    cache_control: "Optional[CacheControlHeader]" = None
    exception_handlers: "Optional[ExceptionHandlersMap]" = None
    guards: "Optional[list[Guard]]" = None
    middleware: "Optional[Sequence[Middleware]]" = None
    opt: "Optional[dict[str, Any]]" = None
    security: "Optional[Sequence[SecurityRequirement]]" = None
    tags: "Optional[Sequence[str]]" = None


class ViteProcess:
    """Manages the Vite process."""

    def __init__(self) -> None:
        self.process: "Optional[subprocess.Popen]" = None  # pyright: ignore[reportUnknownMemberType,reportMissingTypeArgument]
        self._lock = threading.Lock()

    def start(self, command: "list[str]", cwd: "Union[Path, str, None]") -> None:
        """Start the Vite process."""

        try:
            with self._lock:
                if self.process and self.process.poll() is None:  # pyright: ignore[reportUnknownMemberType]
                    return

                self.process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    shell=platform.system() == "Windows",
                )
        except Exception as e:
            console.print(f"[red]Failed to start Vite process: {e!s}[/]")
            raise

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the Vite process."""

        try:
            with self._lock:
                if self.process and self.process.poll() is None:  # pyright: ignore[reportUnknownMemberType]
                    # Send SIGTERM to child process
                    if hasattr(signal, "SIGTERM"):
                        self.process.terminate()  # pyright: ignore[reportUnknownMemberType]
                    try:
                        self.process.wait(timeout=timeout)  # pyright: ignore[reportUnknownMemberType]
                    except subprocess.TimeoutExpired:
                        # Force kill if still alive
                        if hasattr(signal, "SIGKILL"):
                            self.process.kill()  # pyright: ignore[reportUnknownMemberType]
                        self.process.wait(timeout=1.0)  # pyright: ignore[reportUnknownMemberType]
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            raise


class VitePlugin(InitPluginProtocol, CLIPlugin):
    """Vite plugin."""

    __slots__ = ("_asset_loader", "_config", "_static_files_config", "_vite_process")

    def __init__(
        self,
        config: "Optional[ViteConfig]" = None,
        asset_loader: "Optional[ViteAssetLoader]" = None,
        static_files_config: "Optional[StaticFilesConfig]" = None,
    ) -> None:
        """Initialize ``Vite``.

        Args:
            config: configuration to use for starting Vite.  The default configuration will be used if it is not provided.
            asset_loader: an initialized asset loader to use for rendering asset tags.
            static_files_config: optional configuration dictionary for the static files router.
        """
        from litestar_vite.config import ViteConfig

        if config is None:
            config = ViteConfig()
        self._config = config
        self._asset_loader = asset_loader
        self._vite_process = ViteProcess()
        self._static_files_config: "dict[str, Any]" = static_files_config.__dict__ if static_files_config else {}

    @property
    def config(self) -> "ViteConfig":
        return self._config

    @property
    def asset_loader(self) -> "ViteAssetLoader":
        from litestar_vite.loader import ViteAssetLoader

        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader.initialize_loader(config=self._config)
        return self._asset_loader

    def on_cli_init(self, cli: "Group") -> None:
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Returns:
            The :class:`AppConfig <litestar.config.app.AppConfig>` instance.
        """
        from litestar_vite.loader import render_asset_tag, render_hmr_client

        if JINJA_INSTALLED:
            from litestar.contrib.jinja import JinjaTemplateEngine

            if (
                app_config.template_config  # pyright: ignore[reportUnknownMemberType]
                and isinstance(app_config.template_config.engine_instance, JinjaTemplateEngine)  # pyright: ignore[reportUnknownMemberType]
            ):
                app_config.template_config.engine_instance.register_template_callable(  # pyright: ignore[reportUnknownMemberType]
                    key="vite_hmr",
                    template_callable=render_hmr_client,
                )
                app_config.template_config.engine_instance.register_template_callable(  # pyright: ignore[reportUnknownMemberType]
                    key="vite",
                    template_callable=render_asset_tag,
                )
        if self._config.set_static_folders:
            static_dirs = [Path(self._config.bundle_dir), Path(self._config.resource_dir)]
            if Path(self._config.public_dir).exists() and self._config.public_dir != self._config.bundle_dir:
                static_dirs.append(Path(self._config.public_dir))
            base_config = {
                "directories": static_dirs if self._config.dev_mode else [Path(self._config.bundle_dir)],
                "path": self._config.asset_url,
                "name": "vite",
                "html_mode": False,
                "include_in_schema": False,
                "opt": {"exclude_from_auth": True},
            }
            static_files_config: dict[str, Any] = {**base_config, **self._static_files_config}
            app_config.route_handlers.append(create_static_files_router(**static_files_config))
        return app_config

    @contextmanager
    def server_lifespan(self, app: "Litestar") -> "Iterator[None]":
        """Manage Vite server process lifecycle.

        Args:
            app: The :class:`Litestar <litestar.app.Litestar>` instance.

        Yields:
            An iterator of None.
        """
        if self._config.set_environment:
            set_environment(config=self._config)
        if self._config.use_server_lifespan and self._config.dev_mode:
            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self.config.hot_reload:
                console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
            else:
                console.rule("[yellow]Starting Vite watch and build process[/]", align="left")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                yield
            finally:
                self._vite_process.stop()
                console.print("[yellow]Vite process stopped.[/]")
        else:
            yield
