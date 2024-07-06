from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, Request, get
from litestar.connection.base import AuthT, StateT, UserT  # noqa: TCH002
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash  # pyright: ignore[reportUnknownVariableType]
from litestar.stores.memory import MemoryStore
from msgspec import Struct

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.inertia import InertiaConfig, InertiaPlugin

here = Path(__file__).parent


class Message(Struct):
    message: str


class WebController(Controller):
    """Web Controller."""

    opt = {"exclude_from_auth": True}

    @get("/", component="Home")
    async def index(self, request: Request[UserT, AuthT, StateT]) -> Message:
        """Serve site root."""
        flash(request, "Oh no! I've been flashed!", category="error")
        return Message(message="welcome")

    @get("/dashboard/", component="Dashboard")
    async def dashboard(self, request: Request[UserT, AuthT, StateT]) -> Message:
        """Serve site root."""
        flash(request, "Oh no! I've been flashed!", category="error")
        return Message(message="dashboard details")


vite = VitePlugin(
    config=ViteConfig(
        hot_reload=True,
        port=3006,
        use_server_lifespan=True,
        dev_mode=True,
        template_dir="resources/templates/",
    ),
)
inertia = InertiaPlugin(config=InertiaConfig(root_template="index.html"))
flasher = FlashPlugin(config=FlashConfig(template_config=vite.template_config))

app = Litestar(
    plugins=[vite, flasher, inertia],
    route_handlers=[WebController],
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": MemoryStore()},
)
