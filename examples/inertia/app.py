"""Vue Inertia example - server-driven SPA with Vue and Inertia.js.

This example demonstrates using Inertia.js with Vue for a server-driven
single-page application experience.
"""

from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin
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
    return Message(message="Welcome to Inertia!")


@get("/dashboard", component="Dashboard")
async def dashboard() -> Message:
    """Serve the dashboard page."""
    return Message(message="Dashboard content")


vite = VitePlugin(config=ViteConfig(dev_mode=True))
inertia = InertiaPlugin(config=InertiaConfig(root_template="index.html"))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))
flasher = FlashPlugin(config=FlashConfig(template_config=templates))

app = Litestar(
    route_handlers=[index, dashboard],
    plugins=[vite, flasher, inertia],
    template_config=templates,
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": MemoryStore()},
    debug=True,
)
