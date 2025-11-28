"""Basic template example - Jinja2 templates with Vite assets.

This example demonstrates using Jinja2 templates with Vite for
asset bundling and HMR.
"""

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template import TemplateConfig

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


vite = VitePlugin(config=ViteConfig(dev_mode=True, types=False))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[WebController],
    plugins=[vite],
    template_config=templates,
    debug=True,
)
