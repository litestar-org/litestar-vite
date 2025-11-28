from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template import TemplateConfig

from litestar_vite import ViteConfig, VitePlugin

here = Path(__file__).parent


@get("/")
async def index() -> Template:
    return Template(template_name="index.html", context={"title": "Vite + Litestar App"})


vite = VitePlugin(config=ViteConfig(dev_mode=True))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[index],
    plugins=[vite],
    template_config=templates,
    debug=True,
)
