from pathlib import Path

from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin

here = Path(__file__).parent

template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=Path(here / "web" / "templates")))
vite = VitePlugin(
    config=ViteConfig(
        paths=PathConfig(bundle_dir=Path(here / "web" / "public"), resource_dir=Path(here / "web" / "resources")),
        runtime=RuntimeConfig(dev_mode=True),
    )
)
app = Litestar(plugins=[vite], template_config=template_config)
