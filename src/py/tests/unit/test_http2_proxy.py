"""Tests for HTTP/2 proxy functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


async def test_proxy_uses_http2_by_default(monkeypatch: pytest.MonkeyPatch, hotfile: Path) -> None:
    """Ensure HTTP/2 is enabled by default when h2 package is available."""
    captured_http2: list[bool] = []

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured_http2.append(kwargs.get("http2", False))
            kwargs["transport"] = httpx.MockTransport(responder)
            # Remove http2 since MockTransport doesn't support it
            kwargs.pop("http2", None)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", MockAsyncClient)

    # Mock h2 as available
    mock_h2 = MagicMock()
    with patch.dict("sys.modules", {"h2": mock_h2}):
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

        middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile, http2=True)
        await middleware(scope, receive, send)  # type: ignore[arg-type]

    # HTTP/2 should be enabled
    assert captured_http2 == [True]


async def test_proxy_falls_back_when_h2_not_installed(monkeypatch: pytest.MonkeyPatch, hotfile: Path) -> None:
    """Ensure proxy falls back to HTTP/1.1 when h2 package is not installed."""
    captured_http2: list[bool] = []

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured_http2.append(kwargs.get("http2", False))
            kwargs["transport"] = httpx.MockTransport(responder)
            kwargs.pop("http2", None)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", MockAsyncClient)

    # Mock h2 as NOT available by making import fail
    import builtins

    original_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "h2":
            raise ImportError("No module named 'h2'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

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

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile, http2=True)
    await middleware(scope, receive, send)  # type: ignore[arg-type]

    # HTTP/2 should be disabled (fallback to HTTP/1.1)
    assert captured_http2 == [False]


async def test_proxy_respects_http2_false_config(monkeypatch: pytest.MonkeyPatch, hotfile: Path) -> None:
    """Ensure HTTP/2 can be explicitly disabled via config."""
    captured_http2: list[bool] = []

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured_http2.append(kwargs.get("http2", False))
            kwargs["transport"] = httpx.MockTransport(responder)
            kwargs.pop("http2", None)
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

    # Explicitly disable HTTP/2
    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile, http2=False)
    await middleware(scope, receive, send)  # type: ignore[arg-type]

    # HTTP/2 should be disabled
    assert captured_http2 == [False]


def test_vite_config_http2_default() -> None:
    """Ensure ViteConfig has http2 enabled by default."""
    from litestar_vite.config import ViteConfig

    config = ViteConfig()
    assert config.http2 is True


def test_vite_config_http2_can_be_disabled() -> None:
    """Ensure ViteConfig http2 can be disabled."""
    from litestar_vite.config import RuntimeConfig, ViteConfig

    config = ViteConfig(runtime=RuntimeConfig(http2=False))
    assert config.http2 is False
