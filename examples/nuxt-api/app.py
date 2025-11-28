"""Nuxt API example - Litestar API backend for Nuxt frontend.

Demonstrates using Litestar as an API backend with a Nuxt.js frontend.
The Vite plugin proxies API requests to Litestar during development.
"""

from litestar import Litestar, get
from msgspec import Struct

from litestar_vite import ViteConfig, VitePlugin


class HealthResponse(Struct):
    status: str


class Message(Struct):
    message: str


@get("/api/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@get("/api/hello")
async def hello() -> Message:
    """Hello world endpoint."""
    return Message(message="Hello from Litestar!")


vite = VitePlugin(config=ViteConfig(dev_mode=True))

app = Litestar(
    route_handlers=[health, hello],
    plugins=[vite],
    debug=True,
)
