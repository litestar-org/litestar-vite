from __future__ import annotations

from typing import TYPE_CHECKING

from click import group, option
from litestar.cli._utils import LitestarGroup, console

if TYPE_CHECKING:
    from litestar import Litestar


@group(cls=LitestarGroup, name="assets")
def vite_group() -> None:
    """Manage Vite Tasks."""


@vite_group.command(  # type: ignore # noqa: PGH003
    name="build",
    help="Building frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_build(app: Litestar, verbose: bool) -> None:  # noqa: ARG001
    """Run vite build."""
    console.rule("[yellow]Starting Vite build process[/]", align="left")
