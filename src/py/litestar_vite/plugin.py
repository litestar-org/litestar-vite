from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, cast

from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import (
    create_static_files_router,  # pyright: ignore[reportUnknownVariableType]
)

from litestar_vite.config import ViteConfig

if TYPE_CHECKING:
    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.config import ViteTemplateConfig
    from litestar_vite.template_engine import ViteTemplateEngine


def set_environment(config: ViteConfig) -> None:
    """Configure environment for easier integration"""
    os.environ.setdefault("ASSET_URL", config.asset_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    os.environ.setdefault("APP_URL", f"http://localhost:{os.environ.get('LITESTAR_PORT',8000)}")
    if config.dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.dev_mode))


class VitePlugin(InitPluginProtocol, CLIPlugin):
    """Vite plugin."""

    __slots__ = ("_config",)

    def __init__(self, config: ViteConfig | None = None) -> None:
        """Initialize ``Vite``.

        Args:
            config: configuration to use for starting Vite.  The default configuration will be used if it is not provided.
        """
        if config is None:
            config = ViteConfig()
        self._config = config

    @property
    def config(self) -> ViteConfig:
        return self._config

    @property
    def template_config(self) -> ViteTemplateConfig[ViteTemplateEngine]:
        from litestar_vite.config import ViteTemplateConfig
        from litestar_vite.template_engine import ViteTemplateEngine

        return ViteTemplateConfig[ViteTemplateEngine](
            engine=ViteTemplateEngine,
            config=self._config,
            directory=self._config.template_dir,
        )

    def on_cli_init(self, cli: Group) -> None:
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """

        if self._config.template_dir is not None:
            app_config.template_config = self.template_config

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
        import threading

        from litestar.cli._utils import console

        from litestar_vite.commands import execute_command

        if self._config.use_server_lifespan and self._config.dev_mode:
            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command
            if self.config.hot_reload:
                console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
            else:
                console.rule("[yellow]Starting Vite watch and build process[/]", align="left")
            if self._config.set_environment:
                set_environment(config=self._config)
            vite_thread = threading.Thread(
                name="vite",
                target=execute_command,
                args=[],
                kwargs={"command_to_run": command_to_run, "cwd": self._config.root_dir},
            )
            try:
                vite_thread.start()
                yield
            finally:
                if vite_thread.is_alive():
                    vite_thread.join(timeout=5)
                console.print("[yellow]Vite process stopped.[/]")

        else:
            manifest_path = Path(f"{self._config.bundle_dir}/{self._config.manifest_name}")
            if manifest_path.exists():
                console.rule(f"[yellow]Serving assets using manifest at `{manifest_path!s}`.[/]", align="left")
            else:
                console.rule(f"[yellow]Serving assets without manifest at `{manifest_path!s}`.[/]", align="left")
            yield
