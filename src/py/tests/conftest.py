from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

from litestar_vite.config import ViteConfig

pytestmark = pytest.mark.anyio
here = Path(__file__).parent


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def test_app_path() -> Generator[Path, None, None]:
    yield Path(here / "test_app" / "web")


@pytest.fixture
def template_config(test_app_path: Path) -> TemplateConfig[JinjaTemplateEngine]:
    return TemplateConfig(engine=JinjaTemplateEngine(directory=test_app_path / "templates"))


# Define a fixture for ViteConfig
@pytest.fixture
def vite_config(test_app_path: Path) -> ViteConfig:
    # Mock the ViteConfig with necessary attributes for testing
    return ViteConfig(
        bundle_dir=test_app_path / "public",
        resource_dir=test_app_path / "resources",
        hot_reload=True,
    )
