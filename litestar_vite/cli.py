from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from click import Context, group, option
from click import Path as ClickPath
from litestar.cli._utils import (
    LitestarEnv,
    LitestarGroup,
)

if TYPE_CHECKING:
    from litestar import Litestar


@group(cls=LitestarGroup, name="assets")
def vite_group() -> None:
    """Manage Vite Tasks."""


@vite_group.command(  # type: ignore # noqa: PGH003
    name="init",
    help="Initialize vite for your project.",
)
@option(
    "--bundle-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path for the built Vite assets.  This is the where the output of `npm run build` will write files.",
    default=None,
    required=False,
)
@option(
    "--resource-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=None,
    required=False,
)
@option(
    "--asset-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=None,
    required=False,
)
@option("--asset-url", type=str, help="Base url to serve assets from.", default=None, required=False)
@option(
    "--vite-port",
    type=int,
    help="The port to run the vite server against.",
    default=None,
    is_flag=True,
    required=False,
)
@option(
    "--enable-ssr",
    type=bool,
    help="Enable SSR Support.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option("--overwrite", type=bool, help="Overwrite any files in place.", default=False, is_flag=True)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation and use all defaults for initializing the project.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def vite_init(
    ctx: Context,
    vite_port: int | None,
    enable_ssr: bool | None,
    asset_url: str | None,
    asset_path: Path | None,
    bundle_path: Path | None,
    resource_path: Path | None,
    overwrite: bool,
    verbose: bool,
    no_prompt: bool,
) -> None:  # sourcery skip: low-code-quality
    """Run vite build."""
    from litestar.cli._utils import (
        console,
    )
    from rich.prompt import Confirm

    from litestar_vite.commands import init_vite
    from litestar_vite.plugin import VitePlugin

    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    plugin = env.app.plugins.get(VitePlugin)
    config = plugin._config  # noqa: SLF001

    console.rule("[yellow]Initializing Vite[/]", align="left")
    resource_path = resource_path or config.resource_dir
    asset_path = asset_path or config.assets_dir
    bundle_path = bundle_path or config.bundle_dir
    enable_ssr = enable_ssr or config.ssr_enabled
    asset_url = asset_url or config.asset_url
    vite_port = vite_port or config.port
    hot_file = Path(bundle_path / config.hot_file)
    root_path = resource_path.parent
    if any(output_path.exists() for output_path in (asset_path, bundle_path, resource_path)) and not any(
        [overwrite, no_prompt],
    ):
        confirm_overwrite = Confirm.ask(
            "Files were found in the paths specified.  Are you sure you wish to overwrite the contents?",
        )
        if not confirm_overwrite:
            console.print("Skipping Vite initialization")
            sys.exit(2)
    for output_path in (asset_path, bundle_path, resource_path):
        output_path.mkdir(parents=True, exist_ok=True)
    enable_ssr = (
        True
        if enable_ssr
        else False
        if no_prompt
        else Confirm.ask(
            "Do you intend to use Litestar with any SSR framework?",
        )
    )
    init_vite(
        app=env.app,
        root_path=root_path,
        enable_ssr=enable_ssr,
        vite_port=vite_port,
        asset_url=asset_url,
        resource_path=resource_path,
        asset_path=asset_path,
        bundle_path=bundle_path,
        hot_file=hot_file,
        litestar_port=env.port or 8000,
    )


@vite_group.command(  # type: ignore # noqa: PGH003
    name="install",
    help="Install frontend packages.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_install(app: Litestar, verbose: bool) -> None:
    """Run vite build."""
    from litestar.cli._utils import (
        console,
    )

    from litestar_vite.commands import run_vite
    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True
    console.rule("[yellow]Starting Vite package installation process[/]", align="left")
    plugin = app.plugins.get(VitePlugin)
    run_vite(" ".join(plugin._config.install_command))  # noqa: SLF001


@vite_group.command(  # type: ignore # noqa: PGH003
    name="build",
    help="Building frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_build(app: Litestar, verbose: bool) -> None:
    """Run vite build."""
    from litestar.cli._utils import (
        console,
    )

    from litestar_vite.commands import run_vite
    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True
    console.rule("[yellow]Starting Vite build process[/]", align="left")
    plugin = app.plugins.get(VitePlugin)
    run_vite(" ".join(plugin._config.build_command))  # noqa: SLF001


@vite_group.command(  # type: ignore # noqa: PGH003
    name="serve",
    help="Serving frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_serve(app: Litestar, verbose: bool) -> None:
    """Run vite serve."""
    from litestar.cli._utils import (
        console,
    )

    from litestar_vite.commands import run_vite
    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    if plugin._config.hot_reload:  # noqa: SLF001
        console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
    else:
        console.rule("[yellow]Starting Vite watch and build process[/]", align="left")
    command_to_run = (
        plugin._config.run_command if plugin._config.hot_reload else plugin._config.build_watch_command  # noqa: SLF001
    )
    run_vite(" ".join(command_to_run))
