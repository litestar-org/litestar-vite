"""Flash messages example - demonstrates Litestar flash plugin with Vite."""

from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, Request, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash
from litestar.response import Template
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


class WebController(Controller):
    """Web Controller."""

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get("/")
    async def index(self, request: Request[Any, Any, Any]) -> Template:
        """Serve site root."""
        flash(request, "Oh no! I've been flashed!", category="error")

        return Template(template_name="index.html.j2")


templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))
vite = VitePlugin(config=ViteConfig(dev_mode=True))
flasher = FlashPlugin(config=FlashConfig(template_config=templates))

app = Litestar(
    plugins=[vite, flasher],
    route_handlers=[WebController],
    middleware=[ServerSideSessionConfig().middleware],
    template_config=templates,
    stores={"sessions": MemoryStore()},
)
