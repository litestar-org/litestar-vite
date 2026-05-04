"""Regression coverage for sync Inertia props rendered in the handler DI scope."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from litestar import Request, get
from litestar.di import Provide
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, SPAConfig, ViteConfig
from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.helpers import defer, once, optional, share
from litestar_vite.inertia.response import InertiaResponse, _InertiaSSRResult
from litestar_vite.plugin import VitePlugin


class _FakeConnection:
    """Stand-in for a yielded request-scoped database resource."""

    def __init__(self) -> None:
        self.released = False

    def fetch(self) -> str:
        if self.released:
            msg = "cannot call Connection.fetch(): connection has been released back to the pool"
            raise RuntimeError(msg)
        return "ok"


async def _provide_conn() -> AsyncGenerator[_FakeConnection, None]:
    conn = _FakeConnection()
    try:
        yield conn
    finally:
        conn.released = True


def _build_hybrid_plugins(tmp_path: Path) -> tuple[InertiaPlugin, VitePlugin]:
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head></head><body><div id="app"></div></body></html>'
    )
    inertia_config = InertiaConfig(root_template="index.html", ssr=InertiaSSRConfig())
    return (
        InertiaPlugin(config=inertia_config),
        VitePlugin(
            config=ViteConfig(
                mode="hybrid",
                paths=PathConfig(resource_dir=resource_dir),
                runtime=RuntimeConfig(dev_mode=False),
                spa=SPAConfig(app_selector="#app"),
                inertia=inertia_config,
            )
        ),
    )


def _inertia_partial_headers(*, key: str, component: str = "Home") -> dict[str, str]:
    return {
        InertiaHeaders.ENABLED.value: "true",
        InertiaHeaders.PARTIAL_DATA.value: key,
        InertiaHeaders.PARTIAL_COMPONENT.value: component,
    }


async def test_dict_handler_sync_once_prop_runs_inside_di_scope(tmp_path: Path) -> None:
    """Dict handlers should render sync once props before yield-based DI cleanup."""
    inertia_plugin, vite_plugin = _build_hybrid_plugins(tmp_path)
    released_observations: list[bool] = []

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> dict[str, Any]:
        def fetch_recent() -> str:
            released_observations.append(conn.released)
            return conn.fetch()

        return {"recent": once("recent", fetch_recent)}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body='<div id="app">SSR</div>'),
    ):
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    assert "SSR" in response.text
    assert released_observations == [False]


async def test_dict_handler_sync_defer_prop_runs_inside_di_scope(tmp_path: Path) -> None:
    """Sync deferred props should resolve before yield-based DI cleanup on partial reloads."""
    inertia_plugin, vite_plugin = _build_hybrid_plugins(tmp_path)
    released_observations: list[bool] = []

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> dict[str, Any]:
        def fetch_stats() -> str:
            released_observations.append(conn.released)
            return conn.fetch()

        return {"stats": defer("stats", fetch_stats)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="stats"))

    assert response.status_code == 200, response.text
    assert response.json()["props"]["stats"] == "ok"
    assert released_observations == [False]


async def test_dict_handler_sync_optional_prop_runs_inside_di_scope_on_partial_reload(tmp_path: Path) -> None:
    """Sync optional props should resolve before yield-based DI cleanup when requested."""
    inertia_plugin, vite_plugin = _build_hybrid_plugins(tmp_path)
    released_observations: list[bool] = []

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> dict[str, Any]:
        def fetch_recent() -> str:
            released_observations.append(conn.released)
            return conn.fetch()

        return {"recent": optional("recent", fetch_recent)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="recent"))

    assert response.status_code == 200, response.text
    assert response.json()["props"]["recent"] == "ok"
    assert released_observations == [False]


async def test_dict_handler_shared_props_close_over_di_dep(tmp_path: Path) -> None:
    """Shared sync props should render inside the same DI-safe prepass."""
    inertia_plugin, vite_plugin = _build_hybrid_plugins(tmp_path)
    released_observations: list[bool] = []

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> dict[str, Any]:
        def fetch_user() -> str:
            released_observations.append(conn.released)
            return conn.fetch()

        share(request, "user", once("user", fetch_user))
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body='<div id="app">SSR</div>'),
    ):
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    assert released_observations == [False]


async def test_explicit_inertia_response_path_unchanged(tmp_path: Path) -> None:
    """Explicit InertiaResponse returns should keep their existing DI-safe path."""
    inertia_plugin, vite_plugin = _build_hybrid_plugins(tmp_path)
    released_observations: list[bool] = []

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> InertiaResponse[dict[str, Any]]:
        def fetch_recent() -> str:
            released_observations.append(conn.released)
            return conn.fetch()

        return InertiaResponse({"recent": once("recent", fetch_recent)})

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body='<div id="app">SSR</div>'),
    ):
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    assert released_observations == [False]
