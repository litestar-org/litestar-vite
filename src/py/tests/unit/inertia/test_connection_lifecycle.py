"""Regression for asyncpg connection-release bug.

Async prop callbacks (``optional()``/``defer()``/``lazy()``/``once()``) that
close over a yield-based DI dependency must run *inside* Litestar's DI
``AsyncExitStack`` frame, otherwise the dependency's ``__aexit__`` runs first
and the captured resource is unusable.

The current implementation defers async resolution to ASGI dispatch
(``_AsyncInertiaASGIResponse.__call__`` in
``src/py/litestar_vite/inertia/response.py``), which runs *after*
``_call_handler_function``'s ``async with stack:`` exits. By that time, any
yield-based DI dependency (sqlspec asyncpg ``provide_connection``,
advanced-alchemy session, etc.) has already been cleaned up — the connection
is back in the pool, and ``cursor.fetch()`` raises::

    asyncpg.InterfaceError: cannot call Connection.fetch():
    connection has been released back to the pool

These tests exercise that lifecycle with a fake async resource (a
``_FakeConnection`` that flips ``released = True`` on ``__aexit__``).

References:
- https://github.com/litestar-org/litestar-vite/issues/244
- ``.agents/specs/inertia-async-connection-fix/spec.md`` §1.1
"""

from collections.abc import AsyncGenerator
from typing import Any

from litestar import Request, get
from litestar.di import Provide
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.helpers import optional, share
from litestar_vite.plugin import VitePlugin


class _FakeConnection:
    """Stand-in for an asyncpg pool connection.

    ``released`` flips True when the yield-based DI dependency exits. Any
    ``fetch()`` call after that point raises, mimicking
    ``asyncpg.InterfaceError: cannot call Connection.fetch(): connection has
    been released back to the pool``.
    """

    def __init__(self) -> None:
        self.released = False

    async def fetch(self) -> str:
        if self.released:
            msg = "cannot call Connection.fetch(): connection has been released back to the pool"
            raise RuntimeError(msg)
        return "ok"


async def _provide_conn() -> "AsyncGenerator[_FakeConnection, None]":
    """Yield-based DI dependency simulating sqlspec/asyncpg's connection lifecycle.

    Litestar consumes async generators directly — no ``asynccontextmanager``
    wrapper needed. The ``finally`` runs when Litestar's request-scoped
    ``AsyncExitStack`` pops, mimicking sqlspec/asyncpg releasing a connection
    back to the pool.
    """
    conn = _FakeConnection()
    try:
        yield conn
    finally:
        conn.released = True


def _inertia_partial_headers(*, key: str, component: str = "Home") -> "dict[str, str]":
    return {
        InertiaHeaders.ENABLED.value: "true",
        InertiaHeaders.PARTIAL_DATA.value: key,
        InertiaHeaders.PARTIAL_COMPONENT.value: component,
    }


async def test_async_prop_callback_runs_inside_di_scope(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Async ``optional()`` callback closing over a yield-based DI dependency
    must execute before the dependency's ``__aexit__`` releases the resource.

    On the broken implementation, ``_AsyncInertiaASGIResponse.__call__`` runs
    after ``_call_handler_function``'s exit stack pops — ``conn.released`` is
    True by then, and ``conn.fetch()`` raises.
    """

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> "dict[str, Any]":
        async def fetch_recent() -> str:
            return await conn.fetch()

        return {"recent": optional("recent", fetch_recent)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="recent"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["recent"] == "ok"


async def test_defer_async_callback_runs_inside_di_scope(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Same lifecycle requirement, but for ``defer()`` on a partial reload."""

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> "dict[str, Any]":
        async def fetch_stats() -> str:
            return await conn.fetch()

        from litestar_vite.inertia.helpers import defer

        return {"stats": defer("stats", fetch_stats)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="stats"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["stats"] == "ok"


async def test_async_prop_callback_runs_inside_di_scope_without_request_parameter(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Handlers do not need to declare ``request`` for async props to resolve
    before yield-based dependencies are released.
    """

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(conn: _FakeConnection) -> "dict[str, Any]":
        async def fetch_recent() -> str:
            return await conn.fetch()

        return {"recent": optional("recent", fetch_recent)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="recent"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["recent"] == "ok"


async def test_shared_async_prop_callback_runs_inside_di_scope(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Async props registered through ``share()`` use the same DI-safe
    resolution path as route-handler props.
    """

    @get("/", component="Home", dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> "dict[str, Any]":
        async def fetch_recent() -> str:
            return await conn.fetch()

        share(request, "recent", optional("recent", fetch_recent))
        return {}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="recent"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["recent"] == "ok"


async def test_handler_after_request_override_does_not_bypass_resolution(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Handler-level ``after_request`` hooks must not bypass async prop
    resolution inside the DI scope.
    """

    async def user_after_request(response: Any) -> Any:
        return response

    @get("/", component="Home", after_request=user_after_request, dependencies={"conn": Provide(_provide_conn)})
    async def handler(request: Request[Any, Any, Any], conn: _FakeConnection) -> "dict[str, Any]":
        async def fetch_recent() -> str:
            return await conn.fetch()

        return {"recent": optional("recent", fetch_recent)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="recent"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["recent"] == "ok"


async def test_sync_handler_still_works_with_inertia_wrapper(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Wrapping Inertia handlers must preserve Litestar's sync handler path."""

    @get("/", component="Home", sync_to_thread=True)
    def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        return {"value": optional("value", lambda: "ok")}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="value"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["value"] == "ok"


async def test_sync_to_thread_false_handler_still_works_with_inertia_wrapper(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Non-blocking sync handlers are valid when ``sync_to_thread=False``."""

    @get("/", component="Home", sync_to_thread=False)
    def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        return {"value": optional("value", lambda: "ok")}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_partial_headers(key="value"))
        assert response.status_code == 200, response.text
        assert response.json()["props"]["value"] == "ok"
