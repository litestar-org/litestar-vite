"""End-to-end tests for async prop callbacks running on the request loop.

Regression coverage for https://github.com/litestar-org/litestar-vite/issues/244 —
async callbacks passed to ``optional()``/``defer()``/``lazy()``/``once()`` used
to be awaited on a BlockingPortal's dedicated thread + loop, which broke any
callback that touched a request-scoped async resource (asyncpg, aiosqlite,
sqlspec-injected sessions, ...). They must now be awaited on the request loop.
"""

import asyncio
from typing import Any

from litestar import Request, get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.helpers import defer, lazy, once, optional
from litestar_vite.plugin import VitePlugin


def _inertia_headers(*, partial_data: "list[str] | None" = None, component: str = "Home") -> "dict[str, str]":
    headers: "dict[str, str]" = {InertiaHeaders.ENABLED.value: "true"}
    if partial_data is not None:
        headers[InertiaHeaders.PARTIAL_DATA.value] = ",".join(partial_data)
        headers[InertiaHeaders.PARTIAL_COMPONENT.value] = component
    return headers


async def test_optional_async_callback_runs_on_request_loop(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``optional()`` async callback executes on the request's event loop.

    Captures the loop from inside the callback and exposes its id alongside
    the loop id observed by the route handler. They must match, proving the
    callback no longer runs on a separate BlockingPortal loop.
    """

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def fetch_recent() -> "dict[str, Any]":
            return {"callback_loop_id": id(asyncio.get_running_loop()), "handler_loop_id": handler_loop_id}

        return {"recent": optional("recent", fetch_recent)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["recent"]))
        assert response.status_code == 200
        recent = response.json()["props"]["recent"]
        assert recent["callback_loop_id"] == recent["handler_loop_id"]


async def test_defer_async_callback_runs_on_request_loop(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``defer()`` async callback executes on the request loop on partial reload."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def compute_stats() -> "dict[str, Any]":
            return {"callback_loop_id": id(asyncio.get_running_loop()), "handler_loop_id": handler_loop_id}

        return {"stats": defer("stats", compute_stats)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["stats"]))
        stats = response.json()["props"]["stats"]
        assert stats["callback_loop_id"] == stats["handler_loop_id"]


async def test_lazy_async_callback_runs_on_request_loop(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``lazy()`` is the alias of ``defer()`` — same loop guarantee applies."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def compute() -> "dict[str, Any]":
            return {"callback_loop_id": id(asyncio.get_running_loop()), "handler_loop_id": handler_loop_id}

        return {"items": lazy("items", compute)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["items"]))
        items = response.json()["props"]["items"]
        assert items["callback_loop_id"] == items["handler_loop_id"]


async def test_once_async_callback_runs_on_request_loop_initial_load(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``once()`` ships in the initial Inertia payload — its async callback runs on the request loop."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def feature_flags() -> "dict[str, Any]":
            return {"callback_loop_id": id(asyncio.get_running_loop()), "handler_loop_id": handler_loop_id}

        return {"flags": once("flags", feature_flags)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers())
        flags = response.json()["props"]["flags"]
        assert flags["callback_loop_id"] == flags["handler_loop_id"]


async def test_optional_async_not_evaluated_on_initial_load(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``optional()`` callback must NOT run on a full page load (laziness contract)."""

    call_count = {"n": 0}

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        async def cb() -> str:
            call_count["n"] += 1
            return "computed"

        return {"recent": optional("recent", cb)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers())
        assert response.status_code == 200
        assert call_count["n"] == 0


async def test_defer_async_not_evaluated_on_initial_load(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """``defer()`` callback must NOT run on a full page load — it only fires on partial reload."""

    call_count = {"n": 0}

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        async def cb() -> str:
            call_count["n"] += 1
            return "computed"

        return {"stats": defer("stats", cb)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers())
        assert response.status_code == 200
        assert call_count["n"] == 0


async def test_optional_sync_callback_still_works(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Sync ``optional()`` callbacks bypass the resolver and serialize directly."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        return {"v": optional("v", lambda: 42)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["v"]))
        page = response.json()
        assert page["props"]["v"] == 42


async def test_async_callback_uses_request_scoped_state(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Simulates the original failure mode: an async callback that depends on
    a resource bound to the request loop. We use ``asyncio.Event`` (which
    binds to the loop on construction) as a stand-in for asyncpg/aiosqlite —
    awaiting it from a foreign loop raises the same kind of cross-loop error.
    """

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        ready = asyncio.Event()
        ready.set()

        async def cb() -> str:
            await ready.wait()
            return "ok"

        return {"data": optional("data", cb)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["data"]))
        assert response.status_code == 200
        assert response.json()["props"]["data"] == "ok"
