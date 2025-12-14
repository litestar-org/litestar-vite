"""Tests for InertiaMiddleware version mismatch detection."""

from typing import Any

from litestar import Request, get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.plugin import VitePlugin


async def test_version_mismatch_returns_409_with_location_header(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that version mismatch returns 409 with X-Inertia-Location header per Inertia protocol."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/", headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: "wrong-version"}
        )
        # Per Inertia protocol: version mismatch returns 409 Conflict
        assert response.status_code == 409
        # Must include X-Inertia-Location header for client-side hard refresh
        assert InertiaHeaders.LOCATION.value in response.headers
        assert response.headers[InertiaHeaders.LOCATION.value] == "http://testserver.local/"


async def test_version_match_proceeds_normally(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that matching version allows request to proceed."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # First get the current version
        initial_response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        current_version = initial_response.json()["version"]

        # Now make a request with the correct version
        response = client.get(
            "/", headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: current_version}
        )
        # Should return 200 OK with normal Inertia response
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "Home"
        assert data["props"]["data"] == "value"


async def test_non_inertia_request_bypasses_version_check(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that non-Inertia requests bypass version detection."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Request without X-Inertia header (regular browser request)
        response = client.get("/")
        # Should return HTML template, not JSON
        assert response.status_code == 200
        assert response.text.startswith("<!DOCTYPE html>")


async def test_version_header_missing_allows_request(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that Inertia request without version header proceeds (initial load)."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Inertia header present but no version (first visit)
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        # Should proceed normally
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "Home"
        assert "version" in data  # Version is included in response


async def test_version_mismatch_on_different_path(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that version mismatch works correctly with different paths."""

    @get("/about", component="About")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"title": "About Page"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/about", headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: "stale-version"}
        )
        # Should redirect to the requested path
        assert response.status_code == 409
        assert response.headers[InertiaHeaders.LOCATION.value] == "http://testserver.local/about"


async def test_version_mismatch_preserves_query_string(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that version mismatch preserves query parameters in redirect."""

    @get("/search", component="Search")
    async def handler(request: Request[Any, Any, Any], q: str = "") -> dict[str, Any]:
        return {"query": q}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/search?q=test", headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: "old"}
        )
        assert response.status_code == 409
        # URL should include query parameters
        location = response.headers[InertiaHeaders.LOCATION.value]
        assert "q=test" in location
