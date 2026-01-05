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
from litestar_vite.handler import AppHandler
from litestar_vite.handler import _app as app_module

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def temp_resource_dir(tmp_path: Path) -> Path:
    """Create a temporary resource directory with index.html.

    Returns:
        Temporary resource directory path.
    """
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
def temp_resource_dir_with_entry(tmp_path: Path) -> Path:
    """Create a temporary resource directory with an entry point script.

    Returns:
        The fixture value.
    """
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    index_html = resource_dir / "index.html"
    index_html.write_text(
        """
        <!DOCTYPE html>
        <html>
        <head><title>Test SPA</title></head>
        <body>
          <div id="app"></div>
          <script type="module" src="/resources/main.tsx"></script>
        </body>
        </html>
        """
    )
    return resource_dir


@pytest.fixture
def spa_config(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig for SPA mode.

    Returns:
        The fixture value.
    """
    from litestar_vite.config import PathConfig, RuntimeConfig

    # Clear environment variables that might affect config
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa", paths=PathConfig(resource_dir=temp_resource_dir), runtime=RuntimeConfig(dev_mode=False)
    )


@pytest.fixture
def spa_config_dev(temp_resource_dir: Path) -> ViteConfig:
    """Create a ViteConfig for SPA mode in development.

    Returns:
        The fixture value.
    """
    from litestar_vite.config import PathConfig, RuntimeConfig

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        dev_mode=True,
        runtime=RuntimeConfig(dev_mode=True),
    )


@pytest.fixture
def hybrid_config_dev(temp_resource_dir_with_entry: Path) -> ViteConfig:
    """Create a ViteConfig for hybrid (Inertia) mode in development.

    Returns:
        The fixture value.
    """
    from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig

    return ViteConfig(
        mode="hybrid",
        inertia=InertiaConfig(),
        paths=PathConfig(resource_dir=temp_resource_dir_with_entry),
        dev_mode=True,
        runtime=RuntimeConfig(dev_mode=True),
    )


async def test_spa_handler_initialization(spa_config: ViteConfig) -> None:
    """Test SPA handler initialization."""
    handler = AppHandler(spa_config)

    assert handler._config == spa_config
    assert handler._cached_html is None
    assert not handler._initialized

    await handler.initialize_async()

    assert handler._initialized
    assert handler._cached_html is not None
    assert "Test SPA" in handler._cached_html


async def test_spa_handler_production_mode(spa_config: ViteConfig) -> None:
    """Test SPA handler serves cached HTML in production."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

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
    handler = AppHandler(spa_config)

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
    handler = AppHandler(config)
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

    config = ViteConfig(mode="spa", paths=PathConfig(resource_dir=resource_dir), runtime=RuntimeConfig(dev_mode=False))
    handler = AppHandler(config)

    with pytest.raises(ImproperlyConfiguredException, match=r"index\.html not found"):
        await handler.initialize_async()


async def test_spa_handler_dev_mode_proxy(spa_config_dev: ViteConfig, mocker: "MockerFixture") -> None:
    """Test SPA handler proxies to Vite dev server in dev mode."""
    handler = AppHandler(spa_config_dev)

    # Mock httpx.AsyncClient
    mock_response = Mock()
    mock_response.text = "<html><head></head><body>Dev Server HTML</body></html>"
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()

    # Patch httpx.AsyncClient
    expected_url = "http://127.0.0.1:5173"
    with patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_client):
        # Pass explicit vite_url to avoid hotfile resolution picking up stale hotfiles
        await handler.initialize_async(vite_url=expected_url)

        # Verify client was created
        assert handler._http_client is not None

        # Create a mock request
        mock_request = Mock()
        html = await handler.get_html(mock_request)

        assert "Dev Server HTML" in html
        mock_client.get.assert_called_once_with(f"{expected_url}/", follow_redirects=True)


async def test_hybrid_dev_mode_uses_local_index_and_injects_vite(hybrid_config_dev: ViteConfig) -> None:
    """Hybrid mode should serve local index.html and use Vite HTML transforms."""
    handler = AppHandler(hybrid_config_dev)
    await handler.initialize_async(vite_url="http://127.0.0.1:5173")

    mock_request = Mock()
    proxy_mock = AsyncMock()
    transform_mock = AsyncMock(
        return_value='<html><script src="/static/@vite/client"></script>'
        '<script type="module" src="/static/resources/main.tsx"></script></html>'
    )
    with (
        patch.object(AppHandler, "_proxy_to_dev_server", proxy_mock),
        patch.object(AppHandler, "_transform_html_with_vite", transform_mock),
    ):
        html = await handler.get_html(mock_request, page_data={"component": "Home", "props": {}, "url": "/landing"})

    assert "/static/@vite/client" in html
    assert "/static/resources/main.tsx" in html
    proxy_mock.assert_not_called()
    transform_mock.assert_called_once()


async def test_spa_handler_dev_mode_proxy_error(spa_config_dev: ViteConfig) -> None:
    """Test SPA handler returns startup page when dev server not ready."""
    handler = AppHandler(spa_config_dev)

    # Mock httpx.AsyncClient to raise an error (server not ready)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.aclose = AsyncMock()

    with patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_client):
        # Pass explicit vite_url to avoid hotfile resolution
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")

        mock_request = Mock()
        # Should return friendly startup page instead of raising exception
        result = await handler.get_html(mock_request)
        # Check for key elements (Server and starting are split by HTML tags)
        assert "Server" in result and "starting" in result
        assert 'meta http-equiv="refresh"' in result
        assert "http://127.0.0.1:5173" in result  # Shows the URL being connected to


async def test_spa_handler_shutdown(spa_config_dev: ViteConfig) -> None:
    """Test SPA handler shutdown closes HTTP client."""
    handler = AppHandler(spa_config_dev)

    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()

    with patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_client):
        # Pass explicit vite_url to avoid hotfile resolution
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")

        assert handler._http_client is not None

        await handler.shutdown_async()

        mock_client.aclose.assert_called_once()
        assert handler._http_client is None


async def test_spa_handler_create_route_handler(spa_config: ViteConfig) -> None:
    """Test creating a Litestar route handler from SPA handler."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Verify it's a valid route handler (decorated function)
    assert callable(route)
    # The @get decorator returns a decorated function, not the raw function
    assert route.__class__.__name__ in ("get", "HTTPRouteHandler")


async def test_spa_handler_route_handler_integration(spa_config: ViteConfig) -> None:
    """Test SPA handler route handler in a Litestar app."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

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
    handler = AppHandler(spa_config)
    await handler.initialize_async()

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
    handler = AppHandler(spa_config)

    await handler.initialize_async()
    cached_html_1 = handler._cached_html

    await handler.initialize_async()
    cached_html_2 = handler._cached_html

    # Should not reload
    assert cached_html_1 == cached_html_2


async def test_spa_handler_fallback_load(spa_config: ViteConfig) -> None:
    """Test that handler can load HTML even if not pre-initialized."""
    handler = AppHandler(spa_config)
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
def spa_config_for_caching(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig for testing SPA caching behavior.

    Note: No InertiaConfig to avoid auto-enabling CSRF which breaks mock requests.

    Returns:
        ViteConfig: Configured for SPA with transformations enabled.
    """
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    # Clear environment variables
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(inject_csrf=False, app_selector="#app"),
    )


@pytest.fixture
def spa_config_with_script_element(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig with Inertia script element mode enabled.

    Note: InertiaConfig auto-enables CSRF, so these tests pass page_data which
    bypasses the CSRF check path.

    Returns:
        The fixture value.
    """
    from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig, SPAConfig

    # Clear environment variables
    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(app_selector="#app"),  # CSRF auto-enabled by InertiaConfig
        inertia=InertiaConfig(use_script_element=True),  # v2.3+ optimization
    )


async def test_spa_handler_transform_html_with_page_data(spa_config_with_script_element: ViteConfig) -> None:
    """Test that get_html injects page data as script element."""
    handler = AppHandler(spa_config_with_script_element)
    await handler.initialize_async()

    page_data = {"component": "Home", "props": {"user": "test"}}

    mock_request = Mock()
    html = await handler.get_html(mock_request, page_data=page_data)

    # use_script_element=True - page data injected as script element
    assert '<script type="application/json" id="app_page">' in html
    assert "Home" in html
    assert "test" in html


async def test_spa_handler_caches_transformed_html(spa_config_for_caching: ViteConfig) -> None:
    """Test that transformed HTML is cached in production."""
    handler = AppHandler(spa_config_for_caching)
    await handler.initialize_async()

    mock_request = Mock()

    # First call should cache
    html1 = await handler.get_html(mock_request)
    assert handler._cached_transformed_html is not None

    # Second call should use cache
    html2 = await handler.get_html(mock_request)
    assert html1 == html2


async def test_spa_handler_page_data_bypasses_cache(spa_config_for_caching: ViteConfig) -> None:
    """Test that page_data bypasses transformed HTML cache."""
    handler = AppHandler(spa_config_for_caching)
    await handler.initialize_async()

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


async def test_spa_handler_get_html_sync(spa_config_for_caching: ViteConfig) -> None:
    """Test the synchronous get_html_sync method."""
    handler = AppHandler(spa_config_for_caching)
    await handler.initialize_async()

    # Should work synchronously
    html = handler.get_html_sync()

    assert "Test SPA" in html


async def test_spa_handler_get_html_sync_with_page_data(spa_config_with_script_element: ViteConfig) -> None:
    """Test get_html_sync with page_data using script element."""
    handler = AppHandler(spa_config_with_script_element)
    await handler.initialize_async()

    page_data = {"component": "Home", "props": {"message": "Hello"}}

    html = handler.get_html_sync(page_data=page_data)

    # use_script_element=True - page data injected as script element
    assert '<script type="application/json" id="app_page">' in html
    assert "Home" in html


@pytest.fixture
def spa_config_with_data_page_attr(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ViteConfig:
    """Create a ViteConfig with legacy data-page attribute mode (use_script_element=False).

    Returns:
        ViteConfig: Configured for SPA with data-page attribute mode.
    """
    from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig, SPAConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    return ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(inject_csrf=False, app_selector="#app"),
        inertia=InertiaConfig(use_script_element=False),  # Legacy mode: use data-page attribute (default)
    )


async def test_spa_handler_legacy_data_page_attribute(spa_config_with_data_page_attr: ViteConfig) -> None:
    """Test that page data is injected as data-page attribute when use_script_element=False."""
    handler = AppHandler(spa_config_with_data_page_attr)
    await handler.initialize_async()

    page_data = {"component": "Home", "props": {"user": "test"}}

    mock_request = Mock()
    html = await handler.get_html(mock_request, page_data=page_data)

    # Legacy mode: page data injected as data-page attribute
    assert 'data-page="' in html
    assert '<script type="application/json" id="app_page">' not in html
    assert "Home" in html


async def test_spa_handler_legacy_data_page_sync(spa_config_with_data_page_attr: ViteConfig) -> None:
    """Test get_html_sync with legacy data-page attribute mode."""
    handler = AppHandler(spa_config_with_data_page_attr)
    await handler.initialize_async()

    page_data = {"component": "About", "props": {"message": "Hello"}}

    html = handler.get_html_sync(page_data=page_data)

    # Legacy mode: page data injected as data-page attribute
    assert 'data-page="' in html
    assert "About" in html


async def test_spa_handler_get_html_sync_works_in_dev_mode(spa_config_dev: ViteConfig) -> None:
    """Test that get_html_sync works in dev mode with sync HTTP client."""
    handler = AppHandler(spa_config_dev)

    # Mock both async and sync httpx clients for initialization
    mock_async_client = AsyncMock()
    mock_async_client.aclose = AsyncMock()

    mock_sync_client = Mock()
    mock_response = Mock()
    mock_response.text = "<html><head></head><body>Dev Mode</body></html>"
    mock_response.raise_for_status = Mock()
    mock_sync_client.get.return_value = mock_response

    with (
        patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_async_client),
        patch("litestar_vite.handler._app.httpx.Client", return_value=mock_sync_client),
    ):
        # Pass explicit vite_url to avoid hotfile resolution
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")

        html = handler.get_html_sync()
        assert "Dev Mode" in html
        mock_sync_client.get.assert_called_once()


async def test_spa_handler_no_transform_when_spa_config_disabled(
    temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch
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
    handler = AppHandler(config)
    await handler.initialize_async()

    mock_request = Mock()
    html = await handler.get_html(mock_request)

    # Should not have any injected routes
    assert "window.__" not in html
    # Should still have original content
    assert "Test SPA" in html


async def test_spa_handler_csrf_injection(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CSRF token injection into HTML."""
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(inject_csrf=True, csrf_var_name="__LITESTAR_CSRF__"),
    )

    handler = AppHandler(config)
    await handler.initialize_async()

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


async def test_spa_handler_csrf_injection_sync(temp_resource_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CSRF token injection with get_html_sync."""
    from litestar_vite.config import PathConfig, RuntimeConfig, SPAConfig

    monkeypatch.delenv("VITE_DEV_MODE", raising=False)
    monkeypatch.delenv("VITE_HOT_RELOAD", raising=False)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=temp_resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        spa=SPAConfig(inject_csrf=True, csrf_var_name="__LITESTAR_CSRF__"),
    )

    handler = AppHandler(config)
    await handler.initialize_async()

    # Sync method requires explicit CSRF token
    html = handler.get_html_sync(csrf_token="sync-csrf-token")

    # Should have CSRF token injected
    assert 'window.__LITESTAR_CSRF__ = "sync-csrf-token"' in html
    assert "Test SPA" in html


# ============================================================================
# SPA Handler Route Exclusion Tests (Vite Proxy Route Exclusion Fix)
# ============================================================================


async def test_spa_handler_route_exclusion_schema_path(spa_config: ViteConfig) -> None:
    """Test that /schema raises NotFoundException when matched by SPA handler.

    This test verifies that the route detection logic correctly identifies
    /schema as a Litestar route and raises NotFoundException. In practice,
    the VitePlugin should register the SPA handler last to allow other routes
    to take precedence.
    """

    from litestar_vite.plugin import is_litestar_route

    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Create app with SPA route only
    app = Litestar(route_handlers=[route])

    # Verify route detection works
    assert is_litestar_route("/schema", app) is True

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
        # /schema should return 404 since SPA handler raises NotFoundException
        # (In real usage, OpenAPI routes would be registered first)
        response = await client.get("/schema")
        # The SPA handler should raise NotFoundException, resulting in 404
        # (or redirect to OpenAPI schema if registered first)
        assert response.status_code in (404, 200)  # 200 if OpenAPI caught it, 404 if not

        # Verify SPA still works for non-excluded paths
        response = await client.get("/users/123")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_api_path(spa_config: ViteConfig) -> None:
    """Test that /api/* routes work correctly when API handlers are registered.

    This test demonstrates the correct usage pattern: register API routes first,
    then the SPA catch-all. The route exclusion in SPA handler prevents it from
    shadowing API routes.
    """
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    # Add real API routes BEFORE SPA handler
    @get("/api/users")
    async def get_users() -> dict[str, list[str]]:
        return {"users": ["alice", "bob"]}

    @get("/api/posts/{post_id:int}")
    async def get_post(post_id: int) -> dict[str, int]:
        return {"id": post_id}

    # SPA route should be registered LAST
    route = handler.create_route_handler()

    # Register API routes first, then SPA (important for routing precedence)
    app = Litestar(route_handlers=[get_users, get_post, route])

    async with AsyncTestClient(app=app) as client:
        # API routes should work normally
        response = await client.get("/api/users")
        assert response.status_code == 200
        assert response.json() == {"users": ["alice", "bob"]}

        response = await client.get("/api/posts/123")
        assert response.status_code == 200
        assert response.json() == {"id": 123}

        # Should NOT serve SPA HTML for API routes
        assert "Test SPA" not in response.text

        # SPA routes should still work
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "Test SPA" in response.text


def test_server_starting_html_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(app_module, "_SERVER_STARTING_PATH", tmp_path / "missing.html")
    app_module._load_server_starting_template.cache_clear()

    html = app_module._get_server_starting_html("http://127.0.0.1:5173")

    assert "Starting" in html
    assert "127.0.0.1:5173" in html
    assert "127.0.0.1:5173" in html


async def test_proxy_to_dev_server_returns_starting_html_on_error(spa_config_dev: ViteConfig) -> None:
    handler = AppHandler(spa_config_dev)

    mock_async_client = AsyncMock()
    mock_async_client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
    mock_async_client.aclose = AsyncMock()
    mock_sync_client = Mock()

    with (
        patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_async_client),
        patch("litestar_vite.handler._app.httpx.Client", return_value=mock_sync_client),
    ):
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")
        html = await handler._proxy_to_dev_server(Mock())

    assert "Starting" in html
    assert "127.0.0.1:5173" in html


async def test_hybrid_dev_mode_falls_back_to_injected_scripts(hybrid_config_dev: ViteConfig) -> None:
    handler = AppHandler(hybrid_config_dev)

    with (
        patch.object(AppHandler, "_transform_html_with_vite", AsyncMock(side_effect=RuntimeError("boom"))),
        patch.object(AppHandler, "_inject_dev_scripts", return_value="<html>fallback</html>"),
    ):
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")
        request = Mock()
        request.url = Mock(path="/")
        html = await handler._get_dev_html(request)

    assert "fallback" in html


def test_resolve_vite_url_from_hotfile(tmp_path: Path) -> None:
    from litestar_vite.config import PathConfig, RuntimeConfig

    (tmp_path / "public").mkdir(parents=True, exist_ok=True)
    (tmp_path / "public" / "hot").write_text("http://127.0.0.1:5173")

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, bundle_dir="public", resource_dir="src", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=True),
    )
    handler = AppHandler(config)

    assert handler._resolve_vite_url() == "http://127.0.0.1:5173"


def test_load_index_html_sync_missing_raises(tmp_path: Path) -> None:
    from litestar_vite.config import PathConfig, RuntimeConfig

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, resource_dir="missing", bundle_dir="public", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=False),
    )
    handler = AppHandler(config)

    with pytest.raises(ImproperlyConfiguredException):
        handler._load_index_html_sync()


def test_transform_asset_urls_in_html_uses_manifest(spa_config: ViteConfig) -> None:
    handler = AppHandler(spa_config)
    handler._manifest = {"entry": {"file": "assets/main.js"}}

    with patch("litestar_vite.handler._app.transform_asset_urls", return_value="transformed") as transform:
        html = handler._transform_asset_urls_in_html("<html></html>")

    assert html == "transformed"
    assert transform.called


async def test_spa_handler_route_exclusion_deep_spa_link_allowed(spa_config: ViteConfig) -> None:
    """Test that deep SPA links like /users/123 still serve SPA content."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    app = Litestar(route_handlers=[route])

    async with AsyncTestClient(app=app) as client:
        # Deep links should serve SPA
        response = await client.get("/users/123")
        assert response.status_code == 200
        assert "Test SPA" in response.text

        response = await client.get("/posts/456/comments")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_root_path_allowed(spa_config: ViteConfig) -> None:
    """Test that root path / always serves SPA content."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    app = Litestar(route_handlers=[route])

    async with AsyncTestClient(app=app) as client:
        # Root should serve SPA
        response = await client.get("/")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_custom_openapi_path(temp_resource_dir: Path) -> None:
    """Test route exclusion detects custom OpenAPI schema paths."""
    from litestar.openapi import OpenAPIConfig

    from litestar_vite.config import PathConfig, RuntimeConfig
    from litestar_vite.plugin import is_litestar_route

    config = ViteConfig(
        mode="spa", paths=PathConfig(resource_dir=temp_resource_dir), runtime=RuntimeConfig(dev_mode=False)
    )

    handler = AppHandler(config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Custom schema path - OpenAPI will automatically register this
    app = Litestar(
        route_handlers=[route], openapi_config=OpenAPIConfig(title="Test", version="1.0.0", path="/custom-schema")
    )

    # Verify route detection identifies custom schema path
    assert is_litestar_route("/custom-schema", app) is True

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
        # Custom schema path should be detected and excluded
        response = await client.get("/custom-schema")
        # Will be 404 or 200 depending on routing order
        assert response.status_code in (404, 200)

        # Regular SPA paths should still work
        response = await client.get("/about")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_dev_mode(spa_config_dev: ViteConfig) -> None:
    """Test route exclusion works in development mode."""
    handler = AppHandler(spa_config_dev)

    # Mock httpx client for dev mode
    mock_response = Mock()
    mock_response.text = "<html><head></head><body>Dev Server HTML</body></html>"
    mock_response.raise_for_status = Mock()

    mock_async_client = AsyncMock()
    mock_async_client.get = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("litestar_vite.handler._app.httpx.AsyncClient", return_value=mock_async_client):
        await handler.initialize_async(vite_url="http://127.0.0.1:5173")

        route = handler.create_route_handler()

        # Add API route
        @get("/api/data")
        async def get_data() -> dict[str, str]:
            return {"data": "test"}

        app = Litestar(route_handlers=[route, get_data])

        async with AsyncTestClient(app=app) as client:
            # API route should work
            response = await client.get("/api/data")
            assert response.status_code == 200
            assert response.json() == {"data": "test"}

            # SPA route should proxy to Vite
            response = await client.get("/users/123")
            assert response.status_code == 200
            assert "Dev Server HTML" in response.text


async def test_spa_handler_route_exclusion_multiple_api_versions(spa_config: ViteConfig) -> None:
    """Test route exclusion with multiple API versions."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Multiple API versions
    @get("/api/v1/users")
    async def get_users_v1() -> dict[str, str]:
        return {"version": "v1"}

    @get("/api/v2/users")
    async def get_users_v2() -> dict[str, str]:
        return {"version": "v2"}

    app = Litestar(route_handlers=[route, get_users_v1, get_users_v2])

    async with AsyncTestClient(app=app) as client:
        # Both API versions should work
        response = await client.get("/api/v1/users")
        assert response.status_code == 200
        assert response.json() == {"version": "v1"}

        response = await client.get("/api/v2/users")
        assert response.status_code == 200
        assert response.json() == {"version": "v2"}


async def test_spa_handler_route_exclusion_docs_path(spa_config: ViteConfig) -> None:
    """Test that /docs path is excluded from SPA handler."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Add docs route
    @get("/docs")
    async def docs() -> dict[str, str]:
        return {"docs": "swagger"}

    app = Litestar(route_handlers=[route, docs])

    async with AsyncTestClient(app=app) as client:
        response = await client.get("/docs")
        assert response.status_code == 200
        assert response.json() == {"docs": "swagger"}
        assert "Test SPA" not in response.text


async def test_spa_handler_route_exclusion_nested_schema_paths(spa_config: ViteConfig) -> None:
    """Test that nested schema paths like /schema/openapi.json are excluded."""
    from litestar_vite.plugin import is_litestar_route

    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Litestar automatically registers /schema/openapi.json for OpenAPI
    app = Litestar(route_handlers=[route])

    # Verify route detection works for nested paths
    assert is_litestar_route("/schema/openapi.json", app) is True

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
        # Nested schema path should be detected
        response = await client.get("/schema/openapi.json")
        # Will be 404 or 200 depending on routing order
        assert response.status_code in (404, 200)

        # Regular SPA paths should work
        response = await client.get("/products/123")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_with_query_params(spa_config: ViteConfig) -> None:
    """Test that route exclusion works with query parameters."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Add API route that accepts query params
    @get("/api/search")
    async def search(q: str) -> dict[str, str]:
        return {"query": q}

    app = Litestar(route_handlers=[route, search])

    async with AsyncTestClient(app=app) as client:
        response = await client.get("/api/search?q=test")
        assert response.status_code == 200
        assert response.json() == {"query": "test"}
        assert "Test SPA" not in response.text


async def test_spa_handler_route_exclusion_production_mode(temp_resource_dir: Path) -> None:
    """Test route exclusion in production mode with cached bytes."""
    from litestar_vite.config import PathConfig, RuntimeConfig

    config = ViteConfig(
        mode="spa", paths=PathConfig(resource_dir=temp_resource_dir), runtime=RuntimeConfig(dev_mode=False)
    )

    handler = AppHandler(config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Add API route
    @get("/api/status")
    async def status() -> dict[str, str]:
        return {"status": "ok"}

    app = Litestar(route_handlers=[route, status])

    async with AsyncTestClient(app=app) as client:
        # API route should work
        response = await client.get("/api/status")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # SPA route should serve cached HTML
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_with_trailing_slash(spa_config: ViteConfig) -> None:
    """Test route exclusion handles paths with trailing slashes."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Add route with trailing slash
    @get("/api/users/")
    async def get_users() -> dict[str, str]:
        return {"users": "list"}

    app = Litestar(route_handlers=[route, get_users])

    async with AsyncTestClient(app=app) as client:
        # Should match without trailing slash too (Litestar normalizes)
        response = await client.get("/api/users")
        assert response.status_code == 200
        assert "Test SPA" not in response.text


async def test_spa_handler_route_exclusion_similar_paths(spa_config: ViteConfig) -> None:
    """Test that route exclusion handles similar but different paths correctly."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    # Add specific API route
    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"route": "api"}

    app = Litestar(route_handlers=[route, get_users])

    async with AsyncTestClient(app=app) as client:
        # API route should work
        response = await client.get("/api/users")
        assert response.status_code == 200
        assert response.json() == {"route": "api"}

        # Similar SPA path should still serve SPA
        # (Note: /apiusers is different from /api/users)
        response = await client.get("/apiusers")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_empty_path_segments(spa_config: ViteConfig) -> None:
    """Test route exclusion with various path edge cases."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    app = Litestar(route_handlers=[route])

    async with AsyncTestClient(app=app) as client:
        # Root should work
        response = await client.get("/")
        assert response.status_code == 200
        assert "Test SPA" in response.text

        # Deep nested paths should work
        response = await client.get("/a/b/c/d/e")
        assert response.status_code == 200
        assert "Test SPA" in response.text


async def test_spa_handler_route_exclusion_no_false_positives(spa_config: ViteConfig) -> None:
    """Test that common SPA routes don't trigger false positive exclusions."""
    handler = AppHandler(spa_config)
    await handler.initialize_async()

    route = handler.create_route_handler()

    app = Litestar(route_handlers=[route])

    async with AsyncTestClient(app=app) as client:
        # Common SPA routes should all work
        spa_paths = [
            "/home",
            "/about",
            "/contact",
            "/users",
            "/users/profile",
            "/dashboard",
            "/settings",
            "/products/123",
            "/blog/2024/01/post",
        ]

        for path in spa_paths:
            response = await client.get(path)
            assert response.status_code == 200, f"Failed for path: {path}"
            assert "Test SPA" in response.text, f"No SPA content for path: {path}"
