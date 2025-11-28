from __future__ import annotations

from typing import Any

import pytest
from litestar.types import (
    HTTPRequestEvent,
    Receive,
    Scope,
    Send,
)

from litestar_vite.plugin import ViteProxyMiddleware


class _Recorder:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def __call__(self, event: dict[str, Any]) -> None:
        self.events.append(event)


@pytest.mark.anyio
async def test_proxy_http_short_circuits_non_vite_paths() -> None:
    sent = _Recorder()

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})  # type: ignore[arg-type]

    middleware = ViteProxyMiddleware(downstream, "http://127.0.0.1:9999")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/not-a-vite-path",
        "raw_path": b"/not-a-vite-path",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> HTTPRequestEvent:
        return {"type": "http.request", "body": b"", "more_body": False}

    await middleware(scope, receive, sent.__call__)  # type: ignore[arg-type]

    assert any(ev.get("status") == 200 for ev in sent.events)


@pytest.mark.anyio
async def test_proxy_should_proxy_matches_vite_paths() -> None:
    # We don't actually hit upstream; just check that _should_proxy matches prefixes
    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, "http://127.0.0.1:9999")

    assert middleware._should_proxy("/@vite/client")
    assert middleware._should_proxy("/node_modules/.vite/chunk.js")
    assert middleware._should_proxy("/src/main.ts")
    assert middleware._should_proxy("/vite-hmr")
    assert middleware._should_proxy("/@analogjs/vite-plugin-angular")
    assert not middleware._should_proxy("/api/users")
