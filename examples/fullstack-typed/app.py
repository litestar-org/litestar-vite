"""Fullstack typed example with Inertia.js and React.

This example demonstrates a fullstack application with:
- Inertia.js for server-driven SPA routing
- React for the frontend
- OpenAPI type generation via @hey-api/openapi-ts
"""

from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template import TemplateConfig
from msgspec import Struct

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.inertia import InertiaConfig, InertiaPlugin

here = Path(__file__).parent


class Message(Struct):
    message: str


@get("/", component="Home")
async def index() -> Message:
    """Serve the home page."""
    return Message(message="Welcome to fullstack-typed!")


vite = VitePlugin(config=ViteConfig(dev_mode=True))
inertia = InertiaPlugin(config=InertiaConfig(root_template="index.html"))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[index],
    plugins=[vite, inertia],
    template_config=templates,
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": MemoryStore()},
    debug=True,
)
