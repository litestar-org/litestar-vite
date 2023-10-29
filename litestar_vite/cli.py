from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
from anyio import open_process
from anyio.streams.text import TextReceiveStream
from click import group, option
from litestar.cli._utils import LitestarGroup, console

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
@option("--include-vue", type=bool, help="Install and configure Vue automatically.", default=False, is_flag=True)
@option("--include-react", type=bool, help="Include and configure React automatically.", default=False, is_flag=True)
@option("--overwrite", type=bool, help="Overwrite any files in place.", default=False, is_flag=True)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_init(
    app: Litestar,  # noqa: ARG001
    include_vue: bool,
    include_react: bool,
    overwrite: bool,  # noqa: ARG001
    verbose: bool,  # noqa: ARG001
) -> None:
    """Run vite build."""
    console.rule("[yellow]Initializing Vite[/]", align="left")
    if include_vue:
        console.print("Including Vue")
    if include_react:
        console.print("Including React")


@vite_group.command(  # type: ignore # noqa: PGH003
    name="build",
    help="Building frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_build(app: Litestar, verbose: bool) -> None:  # noqa: ARG001
    """Run vite build."""
    console.rule("[yellow]Starting Vite build process[/]", align="left")


@vite_group.command(  # type: ignore # noqa: PGH003
    name="serve",
    help="Serving frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_serve(app: Litestar, verbose: bool) -> None:  # noqa: ARG001
    """Run vite serve."""
    console.rule("[yellow]Starting Vite serve process[/]", align="left")


def run_vite(app: Litestar) -> None:
    """Run Vite in a subprocess."""
    logger = app.get_logger()
    try:
        anyio.run(_run_vite, backend="asyncio", backend_options={"use_uvloop": True})
    except KeyboardInterrupt:
        logger.info("Stopping typescript development services.")
    finally:
        logger.info("Vite Service stopped.")


async def _run_vite(app: Litestar) -> None:
    """Run Vite in a subprocess."""
    logger = app.get_logger()
    plugin = app.plugins.get(VitePlugin)
    async with await open_process(plugin._config.run_command) as vite_process:  # noqa: SLF001
        async for text in TextReceiveStream(vite_process.stdout):  # type: ignore[arg-type]
            logger.info("Vite", message=text.replace("\n", ""))
