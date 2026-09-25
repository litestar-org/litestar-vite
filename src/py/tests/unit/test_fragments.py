"""Unit tests for UI component fragment engine, ComponentResponse, and Jinja2 integration."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from litestar import Litestar, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.testing import create_test_client

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.fragments import ComponentResponse, FragmentEngine, vite_fragment
from litestar_vite.ipc import BaseIPCTransport
from litestar_vite.plugin import VitePlugin


class _StubFragmentTransport(BaseIPCTransport):
    """In-memory IPC transport stub for testing fragment rendering."""

    def __init__(self, response: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self._response = response or {"result": {"html": "<div class=\"card\">Hello</div>"}}
        self._error = error
        self.requests: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return True

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        self.requests.append(payload)
        if self._error is not None:
            raise self._error
        return self._response


def test_fragment_engine_css_extraction_and_cycle_guard(tmp_path: Path) -> None:
    """Verify transitive CSS extraction from manifest.json with cycle detection and Windows path normalization."""
    config = ViteConfig(
        paths=PathConfig(root=tmp_path, resource_dir=Path("resources"), asset_url="/static/"),
        runtime=RuntimeConfig(dev_mode=False),
    )
    loader = MagicMock()
    loader._is_hot_dev = False
    loader._manifest = {
        "resources/components/UserCard.vue": {
            "file": "assets/UserCard-123.js",
            "css": ["assets/UserCard-123.css"],
            "imports": ["_shared-abc.js"],
        },
        "_shared-abc.js": {
            "file": "assets/shared-abc.js",
            "css": ["assets/shared-abc.css"],
            "imports": ["resources/components/UserCard.vue"],
        },
    }
    del loader.get_component_css_urls
    del loader.generate_component_css_tags

    engine = FragmentEngine(config=config, asset_loader=loader, transport=_StubFragmentTransport())
    urls = engine.get_component_css_urls("components\\UserCard.vue")
    assert urls == ["/static/assets/UserCard-123.css", "/static/assets/shared-abc.css"]

    tags = engine.generate_component_css_tags("components/UserCard.vue", newline="\r\n")
    assert tags == (
        '<link rel="stylesheet" href="/static/assets/UserCard-123.css" />\r\n'
        '<link rel="stylesheet" href="/static/assets/shared-abc.css" />'
    )


def test_fragment_engine_dev_mode_omits_non_stylesheet_links(tmp_path: Path) -> None:
    """Verify dev mode does not emit stylesheet links for .vue/.tsx modules to prevent MIME errors."""
    config = ViteConfig(
        paths=PathConfig(root=tmp_path, asset_url="/static/"),
        runtime=RuntimeConfig(dev_mode=True),
    )
    loader = MagicMock()
    loader._is_hot_dev = True
    loader._vite_server_url = lambda p: f"http://127.0.0.1:5173/{p}"
    del loader.get_component_css_urls

    engine = FragmentEngine(config=config, asset_loader=loader, transport=_StubFragmentTransport())
    assert engine.get_component_css_urls("components/Counter.tsx") == []
    assert engine.get_component_css_urls("styles/theme.css") == ["http://127.0.0.1:5173/styles/theme.css"]


@pytest.mark.anyio
async def test_fragment_engine_render_async_and_crlf_preservation(tmp_path: Path) -> None:
    """Verify render_fragment prepends scoped CSS and preserves CRLF line endings."""
    config = ViteConfig(paths=PathConfig(root=tmp_path, asset_url="/static/"))
    loader = MagicMock()
    loader.get_component_css_urls.return_value = ["/static/assets/Card.css"]
    del loader.generate_component_css_tags

    transport = _StubFragmentTransport(response={"result": {"html": "<div>\r\n  <span>Hi</span>\r\n</div>"}})
    engine = FragmentEngine(config=config, asset_loader=loader, transport=transport)

    rendered = await engine.render_fragment("components/Card.vue", props={"id": 7}, mode="static")
    assert rendered == '<link rel="stylesheet" href="/static/assets/Card.css" />\r\n<div>\r\n  <span>Hi</span>\r\n</div>'
    assert transport.requests == [
        {"method": "render_fragment", "params": {"component": "components/Card.vue", "props": {"id": 7}, "mode": "static"}}
    ]


@pytest.mark.anyio
async def test_fragment_engine_raises_on_worker_error(tmp_path: Path) -> None:
    """Verify render_fragment raises ImproperlyConfiguredException when IPC worker returns an error."""
    config = ViteConfig(paths=PathConfig(root=tmp_path))
    loader = MagicMock()
    loader.get_component_css_urls.return_value = []
    del loader.generate_component_css_tags

    transport = _StubFragmentTransport(response={"error": "Component not found"})
    engine = FragmentEngine(config=config, asset_loader=loader, transport=transport)

    with pytest.raises(ImproperlyConfiguredException, match="Component not found"):
        await engine.render_fragment("components/Missing.vue")


def test_component_response_static_and_island_modes(tmp_path: Path) -> None:
    """Verify ComponentResponse renders static HTML and interactive <vite-island> hydration markup."""
    config = ViteConfig(paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    transport = _StubFragmentTransport(response={"result": {"html": "<button>Click 5</button>"}})
    plugin.fragment_engine._transport = transport

    @get("/static-frag")
    async def get_static() -> ComponentResponse:
        return ComponentResponse(component="components/Btn.tsx", props={"count": 5}, mode="static")

    @get("/island-frag")
    async def get_island() -> ComponentResponse:
        return ComponentResponse(component="components/Btn.tsx", props={"count": 5}, mode="island")

    with create_test_client(route_handlers=[get_static, get_island], plugins=[plugin]) as client:
        resp_static = client.get("/static-frag")
        assert resp_static.status_code == 200
        assert resp_static.text == "<button>Click 5</button>"
        assert "<vite-island" not in resp_static.text

        resp_island = client.get("/island-frag")
        assert resp_island.status_code == 200
        assert '<vite-island data-island-component="components/Btn.tsx"' in resp_island.text
        assert "data-island-props=\"{" in resp_island.text or "&quot;count&quot;:5" in resp_island.text
        assert "<button>Click 5</button></vite-island>" in resp_island.text
        assert 'customElements.define("vite-island"' in resp_island.text


def test_vite_fragment_jinja_callable(tmp_path: Path) -> None:
    """Verify vite_fragment Jinja callable merges props and kwargs and returns Markup."""
    config = ViteConfig(paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    transport = _StubFragmentTransport(response={"result": {"html": "<p>Jane</p>"}})
    plugin.fragment_engine._transport = transport

    app = Litestar(route_handlers=[], plugins=[plugin])
    request = MagicMock()
    request.app = app

    markup = vite_fragment({"request": request}, "components/User.vue", props={"role": "admin"}, name="Jane")
    assert str(markup) == "<p>Jane</p>"
    assert transport.requests[-1]["params"]["props"] == {"role": "admin", "name": "Jane"}
