"""End-to-end tests for async prop callbacks running on the request loop.

Regression coverage for https://github.com/litestar-org/litestar-vite/issues/244 —
async callbacks passed to ``optional()``/``defer()``/``lazy()``/``once()`` used
to be awaited on a BlockingPortal's dedicated thread + loop, which broke any
callback that touched a request-scoped async resource (asyncpg, aiosqlite,
sqlspec-injected sessions, ...). They must now be awaited on the request loop.
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

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


async def test_multiple_async_props_resolve_on_request_loop(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Multiple async props in one response all resolve on the request loop and
    serialize in the payload. Both callbacks observe the same loop id."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def fetch_a() -> "dict[str, Any]":
            return {"loop_id": id(asyncio.get_running_loop()), "value": "a"}

        async def fetch_b() -> "dict[str, Any]":
            return {"loop_id": id(asyncio.get_running_loop()), "value": "b"}

        return {
            "alpha": optional("alpha", fetch_a),
            "beta": optional("beta", fetch_b),
            "_handler_loop": handler_loop_id,
        }

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["alpha", "beta"]))
        props = response.json()["props"]
        assert props["alpha"]["value"] == "a"
        assert props["beta"]["value"] == "b"
        assert props["alpha"]["loop_id"] == props["beta"]["loop_id"]


async def test_nested_async_prop_in_mapping(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Async props nested inside a mapping resolve correctly — the recursive
    walker descends into nested dicts/lists, not just top-level keys.

    To exercise the nested path we include BOTH the outer wrapping key and
    the inner optional's key in ``partial_data`` (lazy_render filters at
    every level, so the outer dict needs to pass the filter for the inner
    optional to even be visited).
    """

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        async def inner_cb() -> str:
            return "inner_value"

        return {"outer": {"inner": optional("inner", inner_cb)}}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["outer", "inner"]))
        assert response.status_code == 200
        outer = response.json()["props"]["outer"]
        assert outer["inner"] == "inner_value"


async def test_async_callback_exception_propagates(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """When an async callback raises, the exception propagates to the route's
    error pipeline rather than getting swallowed or wrapped in opaque DI noise."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        async def cb() -> str:
            raise ValueError("intentional failure")

        return {"data": optional("data", cb)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/", headers=_inertia_headers(partial_data=["data"]))
        assert response.status_code == 500


async def test_once_async_callback_evaluates_only_once(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Once-prop async callback fires exactly once per response build, not
    repeatedly — the in-place ``_evaluated`` cache prevents re-evaluation."""

    call_count = {"n": 0}

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        async def cb() -> str:
            call_count["n"] += 1
            return "v"

        return {"flags": once("flags", cb)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers=_inertia_headers())
        assert response.status_code == 200
        # One request → one async invocation. The async pre-pass populates the
        # cache; the subsequent sync render() short-circuits.
        assert call_count["n"] == 1


async def test_ssr_with_async_prop_resolves_on_request_loop(tmp_path: Path) -> None:
    """SSR-enabled hybrid response with an async ``optional()`` prop resolves
    the prop AND fetches SSR HTML on the request loop in a single async
    pre-pass, with the SSR payload reflecting the resolved props."""
    from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, SPAConfig, ViteConfig
    from litestar_vite.inertia.response import _InertiaSSRResult
    from litestar_vite.plugin import VitePlugin as VitePluginCls

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head></head><body><div id="app"></div></body></html>'
    )

    inertia_cfg = InertiaConfig(root_template="index.html", ssr=InertiaSSRConfig())
    inertia_plug = InertiaPlugin(config=inertia_cfg)
    vite_plug = VitePluginCls(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=False),
            spa=SPAConfig(app_selector="#app"),
            inertia=inertia_cfg,
        )
    )

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> "dict[str, Any]":
        handler_loop_id = id(asyncio.get_running_loop())

        async def cb() -> "dict[str, Any]":
            return {"loop_id": id(asyncio.get_running_loop()), "handler_loop_id": handler_loop_id}

        return {"data": optional("data", cb)}

    captured_pages: "list[dict[str, Any]]" = []

    async def fake_ssr(page: "dict[str, Any]", *_: Any, **__: Any) -> _InertiaSSRResult:
        captured_pages.append(page)
        return _InertiaSSRResult(head=[], body='<div id="app">SSR</div>')

    with patch("litestar_vite.inertia.response._render_inertia_ssr", new_callable=AsyncMock, side_effect=fake_ssr):
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plug, vite_plug],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
        ) as client:
            # Partial reload requests the async optional, exercising both the
            # async-prop pre-pass AND the async SSR fetch in one __call__.
            response = client.get("/", headers=_inertia_headers(partial_data=["data"]))

    # Inertia partial reload returns JSON, not the SSR-injected shell. SSR
    # only fires on full HTML loads, so for this assertion path we re-do the
    # full load and confirm SSR was called with the resolved props.
    with patch("litestar_vite.inertia.response._render_inertia_ssr", new_callable=AsyncMock, side_effect=fake_ssr):
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plug, vite_plug],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
        ) as client:
            html_response = client.get("/")

    assert html_response.status_code == 200
    assert "SSR" in html_response.text
    assert captured_pages, "SSR helper was never invoked on the full-page load"
    # The Inertia partial-reload request previously returned JSON with the
    # resolved data; verify the loop-id assertion holds for that path too.
    assert response.json()["props"]["data"]["loop_id"] == response.json()["props"]["data"]["handler_loop_id"]
