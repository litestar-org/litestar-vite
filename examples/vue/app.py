from __future__ import annotations

from pathlib import Path

from litestar import Litestar
from web.controllers import WebController

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent

vite = VitePlugin(
    config=ViteConfig(
        bundle_dir=Path(here / "web" / "public"),
        resource_dir=Path(here / "web" / "resources"),
        assets_dir=Path(here / "web" / "resources" / "assets"),
        templates_dir=Path(here / "web" / "templates"),
        hot_reload=True,
        port=3006,
    ),
)
app = Litestar(plugins=[vite], route_handlers=[WebController])
