"""Angular + Litestar Vite Example.

This example demonstrates using Angular with Vite and the litestar-vite plugin
for seamless integration with a Litestar backend.

The example uses single-port proxy mode where all requests go through Litestar,
which proxies frontend assets to the Vite dev server during development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, get

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

    @get("/data")
    async def get_data(self) -> dict[str, Any]:
        """Return some sample data."""
        return {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ],
            "total": 3,
        }


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
    route_handlers=[APIController],
)
