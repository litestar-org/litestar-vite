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


@pytest.fixture(autouse=True)
def permissive_tmp_path(tmp_path: Path) -> Generator[Path, None, None]:
    tmp_path.chmod(0o775)
    tmp_path.parent.chmod(0o775)
    yield tmp_path


@pytest.fixture
def test_app_path() -> Generator[Path, None, None]:
    yield Path(here / "test_app" / "web")


@pytest.fixture
def template_config(test_app_path: Path) -> Generator[TemplateConfig[JinjaTemplateEngine], None, None]:
    yield TemplateConfig(engine=JinjaTemplateEngine(directory=test_app_path / "templates"))


# Define a fixture for ViteConfig
@pytest.fixture
def vite_config(test_app_path: Path) -> Generator[ViteConfig, None, None]:
    # Mock the ViteConfig with necessary attributes for testing
    yield ViteConfig(
        bundle_dir=test_app_path / "public",
        resource_dir=test_app_path / "resources",
        hot_reload=True,
    )
