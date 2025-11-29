"""Astro API example - Astro frontend with Litestar API backend.

The Astro Vite plugin proxies /api/* requests to this Litestar server.

Run with: litestar run --reload
Astro dev server proxies to http://localhost:8000
"""

from litestar import Litestar, get
from msgspec import Struct

from litestar_vite import TypeGenConfig, ViteConfig, VitePlugin


class Message(Struct):
    message: str


class HealthResponse(Struct):
    status: str


@get("/api/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@get("/api/hello")
async def hello() -> Message:
    """Example API endpoint."""
    return Message(message="Hello from Litestar API!")


vite = VitePlugin(
    config=ViteConfig(
        dev_mode=True,
        types=TypeGenConfig(
            enabled=True,
            output="src/generated",
            openapi_path="src/generated/openapi.json",
            routes_path="src/generated/routes.json",
            generate_zod=True,
            generate_sdk=True,
        ),
    )
)

app = Litestar(
    route_handlers=[health, hello],
    plugins=[vite],
    debug=True,
)
