from __future__ import annotations

import os
import platform
import signal
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, cast

from litestar.cli._utils import console
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]

if TYPE_CHECKING:
    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.config import ViteConfig
    from litestar_vite.loader import ViteAssetLoader


def set_environment(config: ViteConfig) -> None:
    """Configure environment for easier integration"""
    os.environ.setdefault("ASSET_URL", config.asset_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    os.environ.setdefault("APP_URL", f"http://localhost:{os.environ.get('LITESTAR_PORT', 8000)}")
    if config.dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.dev_mode))


class ViteProcess:
    """Manages the Vite process."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None  # pyright: ignore[reportUnknownMemberType,reportMissingTypeArgument]
        self._lock = threading.Lock()

    def start(self, command: list[str], cwd: Path | str | None) -> None:
        """Start the Vite process."""

        try:
            with self._lock:
                if self.process and self.process.poll() is None:  # pyright: ignore[reportUnknownMemberType]
                    return

                console.print(f"Starting Vite process with command: {command}")
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
                console.print("Stopping Vite process")
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            raise


class VitePlugin(InitPluginProtocol, CLIPlugin):
    """Vite plugin."""

    __slots__ = ("_asset_loader", "_config", "_vite_process")

    def __init__(self, config: ViteConfig | None = None, asset_loader: ViteAssetLoader | None = None) -> None:
        """Initialize ``Vite``.

        Args:
            config: configuration to use for starting Vite.  The default configuration will be used if it is not provided.
            asset_loader: an initialized asset loader to use for rendering asset tags.
        """
        from litestar_vite.config import ViteConfig

        if config is None:
            config = ViteConfig()
        self._config = config
        self._asset_loader = asset_loader
        self._vite_process = ViteProcess()

    @property
    def config(self) -> ViteConfig:
        return self._config

    @property
    def asset_loader(self) -> ViteAssetLoader:
        from litestar_vite.loader import ViteAssetLoader

        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader.initialize_loader(config=self._config)
        return self._asset_loader

    def on_cli_init(self, cli: Group) -> None:
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.
        """
        from litestar_vite.loader import render_asset_tag, render_hmr_client

        if app_config.template_config and isinstance(app_config.template_config.engine_instance, JinjaTemplateEngine):  # pyright: ignore[reportUnknownMemberType]
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
            app_config.route_handlers.append(
                create_static_files_router(
                    directories=cast(  # type: ignore[arg-type]
                        "list[Path]",
                        static_dirs if self._config.dev_mode else [Path(self._config.bundle_dir)],
                    ),
                    path=self._config.asset_url,
                    name="vite",
                    html_mode=False,
                    include_in_schema=False,
                    opt={"exclude_from_auth": True},
                ),
            )
        return app_config

    @contextmanager
    def server_lifespan(self, app: Litestar) -> Iterator[None]:
        """Manage Vite server process lifecycle."""

        if self._config.use_server_lifespan and self._config.dev_mode:
            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self.config.hot_reload:
                console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
            else:
                console.rule("[yellow]Starting Vite watch and build process[/]", align="left")

            if self._config.set_environment:
                set_environment(config=self._config)

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                yield
            finally:
                self._vite_process.stop()
                console.print("[yellow]Vite process stopped.[/]")
        else:
            manifest_path = Path(f"{self._config.bundle_dir}/{self._config.manifest_name}")
            if manifest_path.exists():
                console.rule(f"[yellow]Serving assets using manifest at `{manifest_path!s}`.[/]", align="left")
            else:
                console.rule(f"[yellow]Serving assets without manifest at `{manifest_path!s}`.[/]", align="left")
            yield
