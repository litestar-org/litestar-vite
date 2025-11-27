"""Tests for SPA mode handler."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from litestar import Litestar, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.testing import AsyncTestClient

from litestar_vite.config import ViteConfig
from litestar_vite.spa import ViteSPAHandler

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def temp_resource_dir(tmp_path: Path) -> Path:
    """Create a temporary resource directory with index.html."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    index_html = resource_dir / "index.html"
    index_html.write_text(
        """
        <!DOCTYPE html>
        <html>
        <head><title>Test SPA</title></head>
        <body><div id="app"></div></body>
        </html>
        """
    )
    return resource_dir


@pytest.fixture
def spa_config(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig for SPA mode."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    # Clear environment variables that might affect config
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False, hot_reload=False),
    )


@pytest.fixture
def spa_config_dev(temp_resource_dir: Path) -> ViteConfig:
    """Create a ViteConfig for SPA mode in development."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        dev_mode=True,
        runtime=RuntimeConfig(hot_reload=True),
    )


async def test_spa_handler_initialization(spa_config: ViteConfig) -> None:
    """Test SPA handler initialization."""
    handler = ViteSPAHandler(spa_config)

    assert handler._config == spa_config
    assert handler._cached_html is None
    assert not handler._initialized

    await handler.initialize()

    assert handler._initialized
    assert handler._cached_html is not None
    assert "Test SPA" in handler._cached_html


async def test_spa_handler_production_mode(spa_config: ViteConfig) -> None:
    """Test SPA handler serves cached HTML in production."""
    handler = ViteSPAHandler(spa_config)
    await handler.initialize()

    @get("/")
    async def index() -> str:
        return "placeholder"

    app = Litestar(route_handlers=[index])
    async with AsyncTestClient(app=app) as client:
        # Create a mock request by making an actual request
        await client.get("/")
        # Get the request from the app's request scope
        from litestar.connection import Request

        mock_request = Mock(spec=Request)
        mock_request.app = app

        # Get the HTML
        html = await handler.get_html(mock_request)

        assert html is not None
        assert "Test SPA" in html
        assert '<div id="app"></div>' in html


async def test_spa_handler_not_initialized_error(spa_config: ViteConfig) -> None:
    """Test that calling get_html before initialization raises error."""
    handler = ViteSPAHandler(spa_config)

    mock_request = Mock()
    with pytest.raises(ImproperlyConfiguredException, match="not initialized"):
        await handler.get_html(mock_request)


async def test_spa_handler_missing_index_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing index.html raises error."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    # Clear environment variables
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    # No index.html created

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=resource_dir),
        runtime=RuntimeConfig(dev_mode=False, hot_reload=False),
    )
    handler = ViteSPAHandler(config)

    with pytest.raises(ImproperlyConfiguredException, match=r"index\.html not found"):
        await handler.initialize()


async def test_spa_handler_dev_mode_proxy(spa_config_dev: ViteConfig, mocker: MockerFixture) -> None:
    """Test SPA handler proxies to Vite dev server in dev mode."""
    handler = ViteSPAHandler(spa_config_dev)

    # Mock httpx.AsyncClient
    mock_response = Mock()
    mock_response.text = "<html><head></head><body>Dev Server HTML</body></html>"
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()

    # Patch httpx.AsyncClient
    with patch("litestar_vite.spa.httpx.AsyncClient", return_value=mock_client):
        await handler.initialize()

        # Verify client was created
        assert handler._http_client is not None

        # Create a mock request
        mock_request = Mock()
        html = await handler.get_html(mock_request)

        assert "Dev Server HTML" in html
        mock_client.get.assert_called_once_with("/", follow_redirects=True)


async def test_spa_handler_dev_mode_proxy_error(spa_config_dev: ViteConfig) -> None:
    """Test SPA handler handles dev server connection errors."""
    handler = ViteSPAHandler(spa_config_dev)

    # Mock httpx.AsyncClient to raise an error
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.aclose = AsyncMock()

    with patch("litestar_vite.spa.httpx.AsyncClient", return_value=mock_client):
        await handler.initialize()

        mock_request = Mock()
        with pytest.raises(ImproperlyConfiguredException, match="Failed to proxy request"):
            await handler.get_html(mock_request)


async def test_spa_handler_shutdown(spa_config_dev: ViteConfig) -> None:
    """Test SPA handler shutdown closes HTTP client."""
    handler = ViteSPAHandler(spa_config_dev)

    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()

    with patch("litestar_vite.spa.httpx.AsyncClient", return_value=mock_client):
        await handler.initialize()

        assert handler._http_client is not None

        await handler.shutdown()

        mock_client.aclose.assert_called_once()
        assert handler._http_client is None


async def test_spa_handler_create_route_handler(spa_config: ViteConfig) -> None:
    """Test creating a Litestar route handler from SPA handler."""
    handler = ViteSPAHandler(spa_config)
    await handler.initialize()

    route = handler.create_route_handler()

    # Verify it's a valid route handler (decorated function)
    assert callable(route)
    # The @get decorator returns a decorated function, not the raw function
    assert route.__class__.__name__ in ("get", "HTTPRouteHandler")


async def test_spa_handler_route_handler_integration(spa_config: ViteConfig) -> None:
    """Test SPA handler route handler in a Litestar app."""
    handler = ViteSPAHandler(spa_config)
    await handler.initialize()

    route = handler.create_route_handler()

    app = Litestar(route_handlers=[route])

    async with AsyncTestClient(app=app) as client:
        # Test root path
        response = await client.get("/")
        assert response.status_code == 200
        assert "Test SPA" in response.text

        # Test nested path (catch-all)
        response = await client.get("/users/123")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_caches_html(spa_config: ViteConfig, temp_resource_dir: Path) -> None:
    """Test that SPA handler caches HTML and doesn't reload on every request."""
    handler = ViteSPAHandler(spa_config)
    await handler.initialize()

    # Get HTML first time
    mock_request = Mock()
    html1 = await handler.get_html(mock_request)

    # Modify the file on disk
    index_html = temp_resource_dir / "index.html"
    index_html.write_text("<html><body>MODIFIED</body></html>")

    # Get HTML second time - should still be cached
    html2 = await handler.get_html(mock_request)

    assert html1 == html2
    assert "MODIFIED" not in html2
    assert "Test SPA" in html2


async def test_spa_handler_double_initialization(spa_config: ViteConfig) -> None:
    """Test that double initialization is safe (idempotent)."""
    handler = ViteSPAHandler(spa_config)

    await handler.initialize()
    cached_html_1 = handler._cached_html

    await handler.initialize()
    cached_html_2 = handler._cached_html

    # Should not reload
    assert cached_html_1 == cached_html_2


async def test_spa_handler_fallback_load(spa_config: ViteConfig) -> None:
    """Test that handler can load HTML even if not pre-initialized."""
    handler = ViteSPAHandler(spa_config)
    # Don't call initialize()

    handler._initialized = True  # Fake initialization to bypass check
    handler._cached_html = None  # But no cached HTML

    mock_request = Mock()
    html = await handler.get_html(mock_request)

    # Should fallback to loading now
    assert html is not None
    assert "Test SPA" in html
