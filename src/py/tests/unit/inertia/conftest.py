from collections.abc import Generator
from pathlib import Path

import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

from litestar_vite.config import ViteConfig
from litestar_vite.inertia.config import InertiaConfig
from litestar_vite.inertia.plugin import InertiaPlugin
from litestar_vite.plugin import VitePlugin


@pytest.fixture
def inertia_config() -> Generator[InertiaConfig, None, None]:
    yield InertiaConfig(root_template="index.html.j2")


@pytest.fixture
def inertia_plugin(inertia_config: InertiaConfig) -> Generator[InertiaPlugin, None, None]:
    yield InertiaPlugin(config=inertia_config)


@pytest.fixture
def vite_plugin(test_app_path: Path, vite_config: ViteConfig) -> Generator[VitePlugin, None, None]:
    yield VitePlugin(config=vite_config)


@pytest.fixture
def template_config(test_app_path: Path) -> TemplateConfig[JinjaTemplateEngine]:
    return TemplateConfig(engine=JinjaTemplateEngine(directory=Path(__file__).parent / "templates"))
