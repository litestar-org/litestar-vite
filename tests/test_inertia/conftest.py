from pathlib import Path

import pytest

from litestar_vite.inertia.config import InertiaConfig
from litestar_vite.inertia.plugin import InertiaPlugin

pytestmark = pytest.mark.anyio


@pytest.fixture
def inertia_config() -> InertiaConfig:
    return InertiaConfig(root_template=Path(__file__).parent / "templates" / "index.html.j2")


@pytest.fixture
def inertia_plugin(inertia_config: InertiaConfig) -> InertiaPlugin:
    return InertiaPlugin(config=inertia_config)
