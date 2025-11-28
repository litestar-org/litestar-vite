"""HTMX + Alpine.js + Litestar template example.

This example demonstrates using HTMX with Litestar for a progressive enhancement
approach without a full SPA framework.
"""

from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


@get("/")
async def index() -> Template:
    """Serve the home page."""
    return Template(template_name="index.html.j2", context={"project_name": "template-htmx"})


@get("/api/hello")
async def hello() -> str:
    """HTMX API endpoint."""
    return "Hello from Litestar!"


vite = VitePlugin(config=ViteConfig(dev_mode=True))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[index, hello],
    plugins=[vite],
    template_config=templates,
    debug=True,
)
