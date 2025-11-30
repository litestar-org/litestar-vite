from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template import TemplateConfig

from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent


@get("/")
async def index() -> Template:
    return Template(template_name="index.html", context={"title": "Vite + Litestar App"})


vite = VitePlugin(
    config=ViteConfig(
        paths=PathConfig(root=here, resource_dir="resources", bundle_dir="public"),
        types=TypeGenConfig(
            enabled=True,
            output=Path("resources/generated"),
            generate_zod=True,
            generate_sdk=False,
        ),
    )
)
templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)

app = Litestar(
    route_handlers=[index],
    plugins=[vite],
    template_config=templates,
    debug=True,
)
