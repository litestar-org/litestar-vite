"""Flash messages example - demonstrates Litestar flash plugin with Vite."""

import os
from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, Request, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash
from litestar.response import Template
from litestar.template.config import TemplateConfig

from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-secret-key-32c")
session_backend = CookieBackendConfig(secret=SECRET_KEY)


class WebController(Controller):
    """Web Controller."""

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get("/")
    async def index(self, request: Request[Any, Any, Any]) -> Template:
        """Serve site root."""
        flash(request, "Oh no! I've been flashed!", category="error")

        return Template(template_name="index.html.j2")


templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)
vite = VitePlugin(
    config=ViteConfig(
        paths=PathConfig(root=here, resource_dir="resources", bundle_dir="public"),
        types=TypeGenConfig(
            enabled=True,
            output=Path("resources/generated"),
            openapi_path=Path("resources/generated/openapi.json"),
            routes_path=Path("resources/generated/routes.json"),
            generate_zod=True,
            generate_sdk=False,
        ),
    )
)
flasher = FlashPlugin(config=FlashConfig(template_config=templates))

app = Litestar(
    plugins=[vite, flasher],
    route_handlers=[WebController],
    middleware=[session_backend.middleware],
    template_config=templates,
)
