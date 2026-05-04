import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig
from pytest import TempPathFactory

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig

here = Path(__file__).parent


# Environment variables that may affect test behavior - clear before each test
_VITE_ENV_VARS = [
    "VITE_PORT",
    "VITE_HOST",
    "VITE_PROTOCOL",
    "VITE_DEV_MODE",
    "VITE_HOT_RELOAD",
    "VITE_PROXY_MODE",
    "VITE_ALLOW_REMOTE",
    "VITE_HEALTH_CHECK",
    "LITESTAR_PORT",
    "LITESTAR_DEBUG",
    "ASSET_URL",
    # litestar-vite-c1t: bridge config path leaks across tests; force a
    # guaranteed-missing default so consumers fall back to legacy hotfile
    # semantics unless a test explicitly opts in.
    "LITESTAR_VITE_CONFIG_PATH",
]


@pytest.fixture(autouse=True)
def clean_vite_env(tmp_path_factory: TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Clear Vite-related env vars and bridge cache before each test for isolation.

    Also points ``LITESTAR_VITE_CONFIG_PATH`` at a guaranteed-missing path so
    the bridge-config CWD fallback never picks up a developer's stray
    ``.litestar.json`` from the repo root mid-test.

    Returns:
        The result.
    """
    from litestar_vite.utils import read_bridge_config

    for var in _VITE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    sentinel = tmp_path_factory.mktemp("no-bridge") / "missing.json"
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(sentinel))
    read_bridge_config.cache_clear()
    yield
    read_bridge_config.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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
        paths=PathConfig(bundle_dir=test_app_path / "public", resource_dir=test_app_path / "resources"),
        runtime=RuntimeConfig(dev_mode=True),
    )
