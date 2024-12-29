from __future__ import annotations

import shutil
from pathlib import Path
from typing import Generator

import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig
from pytest import TempPathFactory

from litestar_vite.config import ViteConfig

here = Path(__file__).parent


def tmp_path(tmp_path_factory: TempPathFactory) -> Generator[Path, None, None]:
    base_dir = tmp_path_factory.getbasetemp()
    tmp_path = tmp_path_factory.mktemp("pytest")
    yield tmp_path
    if base_dir.exists():
        shutil.rmtree(base_dir, ignore_errors=True)


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
