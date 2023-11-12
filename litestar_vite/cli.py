from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import anyio
from anyio import open_process
from anyio.streams.text import TextReceiveStream
from click import Context, group, option
from click import Path as ClickPath
from litestar.cli._utils import (
    LitestarEnv,
    LitestarGroup,
    console,
)
from rich.prompt import Confirm

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
@option(
    "--include-vue",
    type=bool,
    help="Install and configure Vue automatically.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--include-react",
    type=bool,
    help="Include and configure React automatically.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--include-htmx",
    type=bool,
    help="Install and configure HTMX automatically.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--include-tailwind",
    type=bool,
    help="Include and configure Tailwind CSS automatically.",
    required=False,
    show_default=False,
    is_flag=True,
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
    help="Do not prompt for confirmation before downgrading.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def vite_init(
    ctx: Context,
    vite_port: int,
    include_vue: bool | None,
    include_react: bool | None,
    include_tailwind: bool | None,
    include_htmx: bool | None,
    enable_ssr: bool | None,
    asset_url: str,
    asset_path: Path,
    bundle_path: Path,
    resource_path: Path,
    overwrite: bool,
    verbose: bool,
) -> None:
    """Run vite build."""
    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    console.rule("[yellow]Initializing Vite[/]", align="left")
    _files_exist = (
        True
        if overwrite
        else Confirm.ask(
            "Files were found in the paths specified.  Are you sure you wish to overwrite the contents?",
        )
    )
    include_vue = (
        True
        if include_vue
        else Confirm.ask(
            "Do you want to install and configure Vue?",
        )
    )
    include_react = (
        True
        if include_react
        else Confirm.ask(
            "Do you want to install and configure React?",
        )
    )
    include_tailwind = (
        True
        if include_tailwind
        else Confirm.ask(
            "Do you want to install and configure Tailwind?",
        )
    )
    include_htmx = (
        True
        if include_htmx
        else Confirm.ask(
            "Do you want to install and configure HTMX?",
        )
    )
    enable_ssr = (
        True
        if enable_ssr
        else Confirm.ask(
            "Do you intend to use Litestar with any SSR framework?",
        )
    )
    init_vite(
        app=env.app,
        include_vue=include_vue,
        include_react=include_react,
        include_tailwind=include_tailwind,
        include_htmx=include_htmx,
        enable_ssr=enable_ssr,
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
