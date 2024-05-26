from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, Request, get
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash
from litestar.response import Template

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


class WebController(Controller):
    """Web Controller."""

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get("/")
    async def index(self, request: Request) -> Template:
        """Serve site root."""
        flash(request, "Oh no! I've been flashed!", category="error")

        return Template(template_name="index.html.j2")


vite = VitePlugin(
    config=ViteConfig(
        hot_reload=True,
        port=3006,
        use_server_lifespan=True,
        dev_mode=True,
    ),
)
flasher = FlashPlugin(config=FlashConfig(template_config=vite.template_config))

app = Litestar(plugins=[vite,flasher], route_handlers=[WebController])
