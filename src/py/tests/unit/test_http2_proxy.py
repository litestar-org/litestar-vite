"""Tests for proxy HTTP/2 configuration and AnyIO forwarding."""

from pathlib import Path
from typing import cast

import pytest
from litestar.types import Receive, Scope, Send

from litestar_vite.config import RuntimeConfig, ViteConfig
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


async def test_proxy_forwards_via_anyio_stream(monkeypatch: pytest.MonkeyPatch, hotfile: Path) -> None:
    """Ensure ViteProxyMiddleware forwards requests through AnyIO byte-streaming proxy."""
    captured_targets: list[str] = []

    async def fake_proxy(url: str, *, send: Send, **_kwargs: object) -> None:
        captured_targets.append(url)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    monkeypatch.setattr(proxy_module, "_anyio_proxy_http_request", fake_proxy)

    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = cast(
        "Scope",
        {
            "type": "http",
            "path": "/@vite/client",
            "raw_path": b"/@vite/client",
            "query_string": b"",
            "headers": [],
            "method": "GET",
        },
    )

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile, http2=True)
    await middleware(scope, cast("Receive", receive), cast("Send", send))

    assert captured_targets == ["http://upstream/@vite/client"]
    assert sent[0]["status"] == 200


def test_vite_config_http2_default() -> None:
    """Ensure ViteConfig has http2 enabled by default."""
    config = ViteConfig()
    assert config.http2 is True


def test_vite_config_http2_can_be_disabled() -> None:
    """Ensure ViteConfig http2 can be disabled."""
    config = ViteConfig(runtime=RuntimeConfig(http2=False))
    assert config.http2 is False
