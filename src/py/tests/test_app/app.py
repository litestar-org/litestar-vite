from __future__ import annotations

from pathlib import Path

from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent

template_config = TemplateConfig(
    engine=JinjaTemplateEngine(
        directory=Path(here / "web" / "templates"),
    )
)
vite = VitePlugin(
    config=ViteConfig(
        bundle_dir=Path(here / "web" / "public"),
        resource_dir=Path(here / "web" / "resources"),
        hot_reload=True,
    ),
)
app = Litestar(plugins=[vite], template_config=template_config)
