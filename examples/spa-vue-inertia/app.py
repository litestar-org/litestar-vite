"""Vue 3 + Inertia.js + Litestar Example.

This example demonstrates using Vue 3 with Inertia.js and the litestar-vite plugin
for building modern SPAs with server-side routing.
"""

from pathlib import Path
from typing import Any

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.config import PathConfig
from litestar_vite.inertia import InertiaConfig, InertiaPlugin, InertiaResponse

here = Path(__file__).parent


@get("/")
async def home() -> InertiaResponse:
    """Home page."""
    return InertiaResponse(
        component="Home",
        props={"message": "Welcome to Vue 3 + Inertia.js!"},
    )


@get("/about")
async def about() -> InertiaResponse:
    """About page."""
    return InertiaResponse(
        component="About",
        props={
            "title": "About Us",
            "description": "Learn more about this application.",
        },
    )


@get("/users")
async def users() -> InertiaResponse:
    """Users list page."""
    users_data = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]
    return InertiaResponse(
        component="Users",
        props={"users": users_data},
    )


# API endpoints for demonstration
@get("/api/data")
async def get_data() -> dict[str, Any]:
    """Return sample data."""
    return {
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ],
    }


vite = VitePlugin(
    config=ViteConfig(
        dev_mode=True,
        paths=PathConfig(
            bundle_dir=here / "public",
            resource_dir=here / "resources",
            asset_url="/static/",
        ),
    ),
)

inertia = InertiaPlugin(
    config=InertiaConfig(
        root_template="index.html",
    )
)

app = Litestar(
    plugins=[vite, inertia],
    route_handlers=[home, about, users, get_data],
    template_config=TemplateConfig(
        directory=here / "templates",
        engine=JinjaTemplateEngine,
    ),
)
