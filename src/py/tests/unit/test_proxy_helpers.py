from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from litestar_vite.plugin import VitePlugin
from litestar_vite.plugin._proxy import (
    ViteProxyMiddleware,
    _extract_proxy_response,
    build_hmr_target_url,
    build_proxy_url,
    check_http2_support,
    create_hmr_target_getter,
    create_ssr_proxy_controller,
    create_target_url_getter,
    create_vite_hmr_handler,
    extract_forward_headers,
    extract_subprotocols,
    normalize_proxy_prefixes,
)


class DummyAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def request(self, *_args: object, **_kwargs: object) -> httpx.Response:
        return self._response


pytestmark = pytest.mark.anyio


def test_extract_proxy_response_filters_headers() -> None:
    response = httpx.Response(200, headers={"content-type": "text/plain", "connection": "keep-alive"}, content=b"ok")
    status, headers, body = _extract_proxy_response(response)
    assert status == 200
    assert (b"content-type", b"text/plain") in headers
    assert all(key != b"connection" for key, _ in headers)
    assert body == b"ok"


def test_build_hmr_target_url_includes_query(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    scope = {"path": "/vite-hmr", "query_string": b"token=1"}

    target = build_hmr_target_url(hotfile, scope, "/vite-hmr", "/static/")
    assert target == "ws://localhost:5173/vite-hmr?token=1"


def test_extract_headers_and_subprotocols() -> None:
    scope = {
        "headers": [(b"host", b"example.com"), (b"x-test", b"value"), (b"sec-websocket-protocol", b"json,graphql")]
    }
    assert extract_forward_headers(scope) == [("x-test", "value")]
    assert extract_subprotocols(scope) == ["json", "graphql"]


def test_normalize_proxy_prefixes(tmp_path: Path) -> None:
    prefixes = normalize_proxy_prefixes(
        ("/@vite",),
        asset_url="/static",
        resource_dir=tmp_path / "src",
        bundle_dir=tmp_path / "public",
        root_dir=tmp_path,
    )
    assert "/@vite" in prefixes
    assert "/static/" in prefixes


def test_target_url_getter_caches(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    cached: list[str | None] = [None]
    getter = create_target_url_getter(None, hotfile, cached)

    assert getter() == "http://localhost:5173"
    hotfile.write_text("http://changed:1234")
    assert getter() == "http://localhost:5173"


def test_hmr_target_getter_caches(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    (tmp_path / "hot.hmr").write_text("http://127.0.0.1:24678")

    getter = create_hmr_target_getter(hotfile, [None])
    assert getter() == "http://127.0.0.1:24678"


async def test_proxy_http_with_plugin_client(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", DummyAsyncClient(response))))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "GET",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert events[0]["status"] == 200
    assert events[1]["body"] == b"ok"


async def test_proxy_http_no_target(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/")

    scope = {"method": "GET", "raw_path": b"/@vite/client", "query_string": b"", "headers": [], "path": "/@vite/client"}
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)
    assert events[0]["status"] == 503


async def test_vite_hmr_handler_timeout(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    handler = create_vite_hmr_handler(hotfile)

    socket = MagicMock()
    socket.scope = {"path": "/vite-hmr", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()

    class FailingConnect:
        async def __aenter__(self) -> None:
            raise TimeoutError

        async def __aexit__(self, *_args: object) -> None:
            return None

    with patch("litestar_vite.plugin._proxy.websockets.connect", return_value=FailingConnect()):
        await handler.fn(socket)

    socket.close.assert_called()


async def test_ssr_proxy_http_success() -> None:
    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", DummyAsyncClient(response))))

    Controller = create_ssr_proxy_controller(target="http://localhost:3000", plugin=plugin, http2=False)
    controller = Controller(owner=MagicMock())

    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/", query=""),
        headers={"x-test": "ok"},
        body=AsyncMock(return_value=b""),
    )

    response_obj = await controller.http_proxy.fn(controller, request)
    assert response_obj.status_code == 200


async def test_ssr_proxy_http_no_target() -> None:
    Controller = create_ssr_proxy_controller(target=None, hotfile_path=None, http2=False)
    controller = Controller(owner=MagicMock())

    request = SimpleNamespace(
        method="GET", url=SimpleNamespace(path="/", query=""), headers={}, body=AsyncMock(return_value=b"")
    )

    response_obj = await controller.http_proxy.fn(controller, request)
    assert response_obj.status_code == 503


def test_build_proxy_url_and_http2_support() -> None:
    assert build_proxy_url("http://localhost:3000", "/path", "a=1") == "http://localhost:3000/path?a=1"
    assert build_proxy_url("http://localhost:3000", "/path", "") == "http://localhost:3000/path"
    assert check_http2_support(False) is False
