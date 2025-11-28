"""Angular CLI + Litestar Example.

This example demonstrates using Angular CLI (without Vite) with a Litestar backend.
Angular CLI handles the frontend build process independently, and Litestar serves
the built static files in production.

In development:
- Angular CLI runs on port 4200 with proxy to Litestar (port 8000)
- Use `npm start` to start Angular dev server

In production:
- Angular CLI builds to dist/browser/
- Litestar serves static files from that directory
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, get
from litestar.static_files import create_static_files_router

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


# In production, serve Angular's built files
# The dist/browser directory is created by `ng build`
static_files = create_static_files_router(
    path="/",
    directories=[here / "dist" / "browser"],
    html_mode=True,
)

app = Litestar(
    route_handlers=[APIController, static_files],
)
