"""Regression coverage for Inertia SSR firing when mode='template' (issue #243)."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Literal
from unittest.mock import AsyncMock, patch

from litestar import Request, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.di import Provide
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.inertia import InertiaPlugin
from litestar_vite.inertia.helpers import once
from litestar_vite.inertia.response import _InertiaSSRResult
from litestar_vite.plugin import VitePlugin

TEMPLATES_DIR = Path(__file__).parent / "templates"


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


def _build_plugins(
    tmp_path: Path,
    *,
    mode: Literal["spa", "template"],
    ssr: bool = True,
    target_selector: str = "#app",
    root_template: str = "inertia_ssr.html.j2",
) -> tuple[InertiaPlugin, VitePlugin, TemplateConfig[JinjaTemplateEngine]]:
    """Construct InertiaPlugin/VitePlugin for an Inertia app."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        "<!DOCTYPE html><html><head></head><body><div id='app'>CLIENT_PLACEHOLDER</div></body></html>"
    )
    ssr_config = InertiaSSRConfig(target_selector=target_selector) if ssr else None
    inertia_config = InertiaConfig(root_template=root_template, ssr=ssr_config)
    vite_config = ViteConfig(
        mode=mode,
        paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
        runtime=RuntimeConfig(dev_mode=False),
        inertia=inertia_config,
    )
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=TEMPLATES_DIR))
    return InertiaPlugin(config=inertia_config), VitePlugin(config=vite_config), template_config


def _build_template_plugins(
    tmp_path: Path, *, ssr: bool = True, target_selector: str = "#app", root_template: str = "inertia_ssr.html.j2"
) -> tuple[InertiaPlugin, VitePlugin, TemplateConfig[JinjaTemplateEngine]]:
    """Construct InertiaPlugin/VitePlugin for a template-mode + Inertia app."""
    return _build_plugins(
        tmp_path, mode="template", ssr=ssr, target_selector=target_selector, root_template=root_template
    )


# ===== Core SSR firing =====


async def test_template_mode_ssr_endpoint_invoked(tmp_path: Path) -> None:
    """mode='template' + InertiaConfig(ssr=...) hits the SSR endpoint and injects body into #app."""
    inertia_plugin, vite_plugin, template_config = _build_template_plugins(tmp_path, ssr=True)

    @get("/", component="Home")
    async def handler() -> dict[str, Any]:
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=["<title>SSR_TITLE</title>"], body='<div id="app">SSR_BODY</div>'),
    ) as mock_ssr:
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    mock_ssr.assert_awaited_once()
    assert "SSR_BODY" in response.text
    assert "SSR_TITLE" in response.text
    assert "CLIENT_PLACEHOLDER" not in response.text


async def test_spa_mode_ssr_endpoint_invoked_without_jinja(tmp_path: Path) -> None:
    """mode='spa' + InertiaConfig(ssr=...) hits SSR and uses the SPA index without Jinja."""
    inertia_plugin, vite_plugin, _template_config = _build_plugins(tmp_path, mode="spa", ssr=True)

    @get("/page", component="Home")
    async def handler() -> dict[str, Any]:
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=["<title>SPA_SSR_TITLE</title>"], body='<div id="app">SPA_SSR_BODY</div>'),
    ) as mock_ssr:
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/page")

    assert response.status_code == 200, response.text
    mock_ssr.assert_awaited_once()
    assert "SPA_SSR_BODY" in response.text
    assert "SPA_SSR_TITLE" in response.text
    assert "CLIENT_PLACEHOLDER" not in response.text


async def test_spa_mode_without_ssr_renders_without_jinja(tmp_path: Path) -> None:
    """mode='spa' + InertiaConfig without SSR uses the SPA index and does not require Jinja."""
    inertia_plugin, vite_plugin, _template_config = _build_plugins(tmp_path, mode="spa", ssr=False)

    @get("/page", component="Home")
    async def handler() -> dict[str, Any]:
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body="<div>UNEXPECTED</div>"),
    ) as mock_ssr:
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/page")

    assert response.status_code == 200, response.text
    mock_ssr.assert_not_awaited()
    assert "data-page=" in response.text
    assert "UNEXPECTED" not in response.text


async def test_template_mode_custom_target_selector_respected(tmp_path: Path) -> None:
    """InertiaSSRConfig(target_selector='#root') injects into the #root element instead of #app."""
    inertia_plugin, vite_plugin, template_config = _build_template_plugins(
        tmp_path, ssr=True, target_selector="#root", root_template="inertia_ssr_root.html.j2"
    )

    @get("/", component="Home")
    async def handler() -> dict[str, Any]:
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body='<div id="root">SSR_AT_ROOT</div>'),
    ) as mock_ssr:
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    mock_ssr.assert_awaited_once()
    assert "SSR_AT_ROOT" in response.text
    assert "CLIENT_PLACEHOLDER" not in response.text


async def test_template_mode_no_ssr_config_no_ssr_call(tmp_path: Path) -> None:
    """mode='template' + no ssr_config still renders Jinja with no SSR call (regression guard)."""
    inertia_plugin, vite_plugin, template_config = _build_template_plugins(tmp_path, ssr=False)

    @get("/", component="Home")
    async def handler() -> dict[str, Any]:
        return {"message": "ok"}

    with patch(
        "litestar_vite.inertia.response._render_inertia_ssr",
        new_callable=AsyncMock,
        return_value=_InertiaSSRResult(head=[], body="<div>UNEXPECTED</div>"),
    ) as mock_ssr:
        with create_test_client(
            route_handlers=[handler],
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    mock_ssr.assert_not_awaited()
    assert "CLIENT_PLACEHOLDER" in response.text
    assert "UNEXPECTED" not in response.text


async def test_template_mode_async_props_resolve_inside_di_scope(tmp_path: Path) -> None:
    """Template-mode handlers resolve sync prop closures over yield-based DI deps before cleanup."""
    inertia_plugin, vite_plugin, template_config = _build_template_plugins(tmp_path, ssr=True)
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
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/")

    assert response.status_code == 200, response.text
    assert released_observations == [False]
