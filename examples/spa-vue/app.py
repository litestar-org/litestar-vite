"""Vue 3 + Litestar Vite Example.

This example demonstrates using Vue 3 with Vite and the litestar-vite plugin
for seamless integration with a Litestar backend.
"""

from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.config import PathConfig

here = Path(__file__).parent


class APIController(Controller):
    """API Controller for backend endpoints."""

    path = "/api"

    @get("/hello")
    async def hello(self) -> dict[str, str]:
        """Return a greeting message."""
        return {"message": "Hello from Litestar!"}

    @get("/users")
    async def get_users(self) -> dict[str, Any]:
        """Return sample user data."""
        return {
            "users": [
                {"id": 1, "name": "Alice", "role": "Admin"},
                {"id": 2, "name": "Bob", "role": "User"},
                {"id": 3, "name": "Charlie", "role": "User"},
            ],
        }


@get("/")
async def index() -> Template:
    """Serve the main page."""
    return Template(template_name="index.html")


vite = VitePlugin(
    config=ViteConfig(
        dev_mode=True,
        paths=PathConfig(
            bundle_dir=here / "public",
            resource_dir=here / "src",
            asset_url="/static/",
        ),
    ),
)

app = Litestar(
    plugins=[vite],
    route_handlers=[index, APIController],
    template_config=TemplateConfig(
        directory=here / "templates",
        engine=JinjaTemplateEngine,
    ),
)
