from pathlib import Path
from typing import Any

import httpx
import pytest
from litestar.types import Receive, Scope, Send

from litestar_vite.plugin import ViteProxyMiddleware
from litestar_vite.plugin import _proxy as proxy_module

pytestmark = pytest.mark.anyio


@pytest.fixture
def hotfile(tmp_path: Path) -> Path:
    """Create a hotfile with a test Vite server URL.

    Returns:
        The fixture value.
    """
    hotfile_path = tmp_path / "hot"
    hotfile_path.write_text("http://upstream")
    return hotfile_path


async def test_proxy_http_forwarding(monkeypatch: pytest.MonkeyPatch, hotfile: Path) -> None:
    """Ensure HTTP requests to Vite paths are proxied to the upstream server."""

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"x-upstream": "1"}, text="from-upstream")

    transport = httpx.MockTransport(responder)

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", MockAsyncClient)

    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/@vite/client",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [],
        "method": "GET",
    }

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile)
    await middleware(scope, receive, send)  # type: ignore[arg-type]
    statuses = [m for m in sent if m.get("type") == "http.response.start"]
    bodies = [m for m in sent if m.get("type") == "http.response.body"]
    assert statuses and statuses[0]["status"] == 200
    assert bodies and bodies[0]["body"] == b"from-upstream"


async def test_proxy_returns_503_when_hotfile_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure middleware returns 503 when Vite server is not running (no hotfile)."""
    hotfile_path = tmp_path / "nonexistent_hot"  # Don't create the file

    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/@vite/client",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [],
        "method": "GET",
    }

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile_path)
    await middleware(scope, receive, send)  # type: ignore[arg-type]
    statuses = [m for m in sent if m.get("type") == "http.response.start"]
    bodies = [m for m in sent if m.get("type") == "http.response.body"]
    assert statuses and statuses[0]["status"] == 503
    assert bodies and b"Vite server not running" in bodies[0]["body"]  # type: ignore[operator]
