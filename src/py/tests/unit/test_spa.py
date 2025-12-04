"""Tests for SPA mode handler."""

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
        runtime=RuntimeConfig(dev_mode=False),
    )


@pytest.fixture
def spa_config_dev(temp_resource_dir: Path) -> ViteConfig:
    """Create a ViteConfig for SPA mode in development."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        dev_mode=True,
        runtime=RuntimeConfig(dev_mode=True),
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


@pytest.mark.asyncio
async def test_spa_get_bytes_lazy_initialize(tmp_path: Path) -> None:
    """get_bytes should lazily initialize when lifespan didn't run."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<!doctype html><html></html>")

    config = ViteConfig(
        mode="spa",
        dev_mode=False,
        paths=PathConfig(root=tmp_path, resource_dir=resource_dir, bundle_dir=tmp_path / "public"),
        runtime=RuntimeConfig(dev_mode=False),
    )
    handler = ViteSPAHandler(config)
    # Simulate a worker that never ran initialize()
    handler._initialized = False

    data = await handler.get_bytes()

    assert data.startswith(b"<!doctype html>")


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
        runtime=RuntimeConfig(dev_mode=False),
    )
    handler = ViteSPAHandler(config)

    with pytest.raises(ImproperlyConfiguredException, match=r"index\.html not found"):
        await handler.initialize()


async def test_spa_handler_dev_mode_proxy(spa_config_dev: ViteConfig, mocker: "MockerFixture") -> None:
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
        mock_client.get.assert_called_once_with("http://127.0.0.1:5173/", follow_redirects=True)


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


# ============================================================================
# SPA Handler Transformation Tests
# ============================================================================


@pytest.fixture
def spa_config_with_transforms(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig with SPA transformations enabled.

    Note: inject_csrf is disabled for tests that don't mock the request scope,
    as CSRF token extraction requires a real request with ScopeState.
    """
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    # Clear environment variables
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(
            inject_csrf=False,  # Disable for tests that don't mock request scope
            app_selector="#app",
        ),
    )


async def test_spa_handler_transform_html_with_page_data(
    spa_config_with_transforms: ViteConfig,
) -> None:
    """Test that get_html injects page data."""
    handler = ViteSPAHandler(spa_config_with_transforms)
    await handler.initialize()

    page_data = {"component": "Home", "props": {"user": "test"}}

    mock_request = Mock()
    html = await handler.get_html(mock_request, page_data=page_data)

    # Should contain the injected page data as data-page attribute
    assert 'data-page="' in html
    assert "Home" in html
    assert "test" in html


async def test_spa_handler_caches_transformed_html(
    spa_config_with_transforms: ViteConfig,
) -> None:
    """Test that transformed HTML is cached in production."""
    handler = ViteSPAHandler(spa_config_with_transforms)
    await handler.initialize()

    mock_request = Mock()

    # First call should cache
    html1 = await handler.get_html(mock_request)
    assert handler._cached_transformed_html is not None

    # Second call should use cache
    html2 = await handler.get_html(mock_request)
    assert html1 == html2


async def test_spa_handler_page_data_bypasses_cache(
    spa_config_with_transforms: ViteConfig,
) -> None:
    """Test that page_data bypasses transformed HTML cache."""
    handler = ViteSPAHandler(spa_config_with_transforms)
    await handler.initialize()

    mock_request = Mock()

    # Call without page_data to populate cache
    html_cached = await handler.get_html(mock_request)
    assert handler._cached_transformed_html is not None

    # Call with page_data should get fresh transformation
    page_data = {"component": "About", "props": {}}
    html_with_data = await handler.get_html(mock_request, page_data=page_data)

    # Should have page data
    assert "About" in html_with_data
    # But the cached version shouldn't have page data
    assert "About" not in html_cached


async def test_spa_handler_get_html_sync(
    spa_config_with_transforms: ViteConfig,
) -> None:
    """Test the synchronous get_html_sync method."""
    handler = ViteSPAHandler(spa_config_with_transforms)
    await handler.initialize()

    # Should work synchronously
    html = handler.get_html_sync()

    assert "Test SPA" in html


async def test_spa_handler_get_html_sync_with_page_data(
    spa_config_with_transforms: ViteConfig,
) -> None:
    """Test get_html_sync with page_data."""
    handler = ViteSPAHandler(spa_config_with_transforms)
    await handler.initialize()

    page_data = {"component": "Home", "props": {"message": "Hello"}}

    html = handler.get_html_sync(page_data=page_data)

    assert 'data-page="' in html
    assert "Home" in html


async def test_spa_handler_get_html_sync_works_in_dev_mode(
    spa_config_dev: ViteConfig,
) -> None:
    """Test that get_html_sync works in dev mode with sync HTTP client."""
    handler = ViteSPAHandler(spa_config_dev)

    # Mock both async and sync httpx clients for initialization
    mock_async_client = AsyncMock()
    mock_async_client.aclose = AsyncMock()

    mock_sync_client = Mock()
    mock_response = Mock()
    mock_response.text = "<html><head></head><body>Dev Mode</body></html>"
    mock_response.raise_for_status = Mock()
    mock_sync_client.get.return_value = mock_response

    with (
        patch("litestar_vite.spa.httpx.AsyncClient", return_value=mock_async_client),
        patch("litestar_vite.spa.httpx.Client", return_value=mock_sync_client),
    ):
        await handler.initialize()

        html = handler.get_html_sync()
        assert "Dev Mode" in html
        mock_sync_client.get.assert_called_once()


async def test_spa_handler_no_transform_when_spa_config_disabled(
    temp_resource_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that HTML is not transformed when spa=False."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=False,  # Transformations disabled
    )
    handler = ViteSPAHandler(config)
    await handler.initialize()

    mock_request = Mock()
    html = await handler.get_html(mock_request)

    # Should not have any injected routes
    assert "window.__" not in html
    # Should still have original content
    assert "Test SPA" in html


async def test_spa_handler_csrf_injection(
    temp_resource_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CSRF token injection into HTML."""
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(
            inject_csrf=True,
            csrf_var_name="__LITESTAR_CSRF__",
        ),
    )

    handler = ViteSPAHandler(config)
    await handler.initialize()

    # Mock request with scope that has state
    mock_request = Mock()
    mock_request.scope = {"state": {"csrf_token": "test-csrf-token-12345"}}

    # Patch litestar ScopeState.from_scope to return a mock with our token
    mock_scope_state = Mock()
    mock_scope_state.csrf_token = "test-csrf-token-12345"

    with patch("litestar.utils.scope.state.ScopeState.from_scope", return_value=mock_scope_state):
        html = await handler.get_html(mock_request)

    # Should have CSRF token injected
    assert 'window.__LITESTAR_CSRF__ = "test-csrf-token-12345"' in html
    assert "Test SPA" in html


async def test_spa_handler_csrf_injection_sync(
    temp_resource_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CSRF token injection with get_html_sync."""
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(
            inject_csrf=True,
            csrf_var_name="__LITESTAR_CSRF__",
        ),
    )

    handler = ViteSPAHandler(config)
    await handler.initialize()

    # Sync method requires explicit CSRF token
    html = handler.get_html_sync(csrf_token="sync-csrf-token")

    # Should have CSRF token injected
    assert 'window.__LITESTAR_CSRF__ = "sync-csrf-token"' in html
    assert "Test SPA" in html
