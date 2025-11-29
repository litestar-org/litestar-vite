"""Angular CLI example - uses standard Angular CLI with Litestar backend.

Demonstrates the Vite proxy integration where Litestar serves the
index.html and Angular CLI handles asset bundling with HMR in development.
"""

from pathlib import Path

from anyio import Path as AsyncPath
from litestar import Litestar, get
from litestar.response import Response

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


@get("/")
async def index() -> Response[bytes]:
    """Serve the SPA index.html."""
    content = await AsyncPath(here / "src" / "index.html").read_bytes()
    return Response(content=content, media_type="text/html")


vite = VitePlugin(config=ViteConfig())

app = Litestar(
    route_handlers=[index],
    plugins=[vite],
    debug=True,
)
