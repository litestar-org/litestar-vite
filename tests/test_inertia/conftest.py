from pathlib import Path

import pytest

from litestar_vite.config import ViteConfig
from litestar_vite.inertia.config import InertiaConfig
from litestar_vite.inertia.plugin import InertiaPlugin
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


@pytest.fixture
def inertia_config() -> InertiaConfig:
    return InertiaConfig(root_template="index.html.j2")


@pytest.fixture
def inertia_plugin(inertia_config: InertiaConfig) -> InertiaPlugin:
    return InertiaPlugin(config=inertia_config)


@pytest.fixture
def vite_plugin() -> VitePlugin:
    return VitePlugin(
        config=ViteConfig(
            resource_dir=Path(__file__).parent / "resources",
            template_dir=Path(__file__).parent / "templates",
        ),
    )
