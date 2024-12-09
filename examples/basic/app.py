from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


class WebController(Controller):
    """Web Controller."""

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get("/")
    async def index(self) -> Template:
        """Serve site root."""
        return Template(template_name="index.html.j2")


templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))
vite = VitePlugin(
    config=ViteConfig(
        hot_reload=True,
        port=3006,
        use_server_lifespan=True,
        dev_mode=True,
    ),
)
app = Litestar(plugins=[vite], route_handlers=[WebController], template_config=templates)
