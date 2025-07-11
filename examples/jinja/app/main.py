from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.static_files import StaticFilesConfig
from litestar.template.config import TemplateConfig

from litestar_vite import VitePlugin

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"


@get("/")
async def index() -> Template:
    return Template(template_name="index.html", context={"title": "Vite + Litestar App"})


app = Litestar(
    route_handlers=[index],
    plugins=[VitePlugin()],
    static_files_config=[
        StaticFilesConfig(
            path="/assets",
            directories=[STATIC_DIR / "assets"],
            name="static",
        )
    ],
    template_config=TemplateConfig(
        directory=TEMPLATE_DIR,
        engine=JinjaTemplateEngine,
    ),
    debug=True,
)
