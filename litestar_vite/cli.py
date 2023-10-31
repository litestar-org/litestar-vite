from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import anyio
from anyio import open_process
from anyio.streams.text import TextReceiveStream
from click import group, option
from litestar.cli._utils import LitestarGroup, console

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
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option(
    "--resource-path",
    type=bool,
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=False,
    is_flag=True,
)
@option("--bundle-path", type=bool, help="Install and configure Vue automatically.", default=False, is_flag=True)
@option("--vite-port", type=int, help="The port to run the vite server against.", default=False, is_flag=True)
@option("--include-vue", type=bool, help="Install and configure Vue automatically.", default=False, is_flag=True)
@option("--include-react", type=bool, help="Include and configure React automatically.", default=False, is_flag=True)
@option("--overwrite", type=bool, help="Overwrite any files in place.", default=False, is_flag=True)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_init(
    app: Litestar,
    vite_port: int,
    include_vue: bool,
    include_react: bool,
    bundle_path: Path,
    resource_path: Path,
    overwrite: bool,  # noqa: ARG001
    verbose: bool,  # noqa: ARG001
) -> None:
    """Run vite build."""
    console.rule("[yellow]Initializing Vite[/]", align="left")
    if include_vue:
        console.print("Including Vue")
    if include_react:
        console.print("Including React")
    init_vite(
        app=app,
        include_vue=include_vue,
        include_react=include_react,
        vite_port=vite_port,
        resource_path=resource_path,
        bundle_path=bundle_path,
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
