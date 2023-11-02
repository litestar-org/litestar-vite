from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import anyio
from anyio import open_process
from anyio.streams.text import TextReceiveStream
from click import Context, group, option
from litestar.cli._utils import (
    LitestarEnv,
    LitestarGroup,
    console,
)
from click import Path as ClickPath

from litestar_vite.commands import init_vite
from litestar_vite.plugin import VitePlugin

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
    default=Path(Path.cwd() / "public"),
    required=True,
)
@option(
    "--resource-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=Path(Path.cwd() / "resources/"),
    required=True,
)
@option(
    "--asset-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=Path(Path.cwd() / "resources" / "assets"),
    required=True,
)
@option("--asset-url", type=str, help="Base url to serve assets from.", default="/static/")
@option("--vite-port", type=int, help="The port to run the vite server against.", default=False, is_flag=True)
@option("--include-vue", type=bool, help="Install and configure Vue automatically.", default=False, is_flag=True)
@option("--include-react", type=bool, help="Include and configure React automatically.", default=False, is_flag=True)
@option("--include-htmx", type=bool, help="Install and configure HTMX automatically.", default=False, is_flag=True)
@option(
    "--include-tailwind",
    type=bool,
    help="Include and configure Tailwind CSS automatically.",
    default=False,
    is_flag=True,
)
@option("--overwrite", type=bool, help="Overwrite any files in place.", default=False, is_flag=True)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_init(
    ctx: Context,
    vite_port: int,
    include_vue: bool,
    include_react: bool,
    include_tailwind: bool,
    include_htmx: bool,
    asset_url: str,
    asset_path: Path,
    bundle_path: Path,
    resource_path: Path,
    overwrite: bool,  # noqa: ARG001
    verbose: bool,
) -> None:
    """Run vite build."""
    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    console.rule("[yellow]Initializing Vite[/]", align="left")
    if include_vue:
        console.print("Including Vue")
    if include_react:
        console.print("Including React")
    if include_tailwind:
        console.print("Including tailwind")
    init_vite(
        app=env.app,
        include_vue=include_vue,
        include_react=include_react,
        include_tailwind=include_tailwind,
        vite_port=vite_port,
        asset_url=asset_url,
        resource_path=resource_path,
        asset_path=asset_path,
        bundle_path=bundle_path,
        litestar_port=env.port or 8000,
    )


@vite_group.command(  # type: ignore # noqa: PGH003
    name="build",
    help="Building frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_build(app: Litestar, verbose: bool) -> None:  # noqa: ARG001
    """Run vite build."""
    console.rule("[yellow]Starting Vite build process[/]", align="left")
    run_vite(app, "build")


@vite_group.command(  # type: ignore # noqa: PGH003
    name="serve",
    help="Serving frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_serve(app: Litestar, verbose: bool) -> None:  # noqa: ARG001
    """Run vite serve."""
    console.rule("[yellow]Starting Vite serve process[/]", align="left")
    run_vite(app, "serve")


def run_vite(app: Litestar, command: Literal["serve", "build"]) -> None:
    """Run Vite in a subprocess."""
    logger = app.get_logger()
    try:
        anyio.run(_run_vite, app, command)
    except KeyboardInterrupt:
        logger.info("Stopping typescript development services.")
    finally:
        logger.info("Vite Service stopped.")


async def _run_vite(app: Litestar, command: Literal["serve", "build"]) -> None:
    """Run Vite in a subprocess."""
    logger = app.get_logger()
    plugin = app.plugins.get(VitePlugin)
    command_to_run = plugin._config.build_command if command == "build" else plugin._config.run_command  # noqa: SLF001
    async with await open_process(command_to_run) as vite_process:
        async for text in TextReceiveStream(vite_process.stdout):  # type: ignore[arg-type]
            logger.info("Vite", message=text.replace("\n", ""))
