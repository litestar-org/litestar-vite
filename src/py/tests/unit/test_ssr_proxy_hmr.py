from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest
from litestar import WebSocket
from litestar.exceptions import WebSocketDisconnect

from litestar_vite.plugin import create_ssr_ws_proxy_handler

pytestmark = pytest.mark.anyio


@pytest.fixture
def hotfile(tmp_path: Path) -> Path:
    """Create a hotfile with a test Vite server URL.

    Returns:
        The fixture value.
    """
    hotfile_path = tmp_path / "hot"
    hotfile_path.write_text("http://localhost:3000")
    return hotfile_path


@pytest.fixture
def hmr_hotfile(hotfile: Path) -> Path:
    """Create an HMR hotfile with a distinct HMR port.

    Returns:
        The fixture value.
    """
    hmr_path = Path(f"{hotfile}.hmr")
    hmr_path.write_text("http://127.0.0.1:24678")
    return hmr_path


async def test_ssr_proxy_uses_hmr_target_when_available(hotfile: Path, hmr_hotfile: Path) -> None:
    """The WS HMR proxy prefers the ``hot.hmr`` target over the main dev-server target."""

    handler = create_ssr_ws_proxy_handler(hotfile_path=hotfile)

    # Mock WebSocket
    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    # Raise WebSocketDisconnect(code=1000) to simulate client disconnect and stop the loop
    socket.receive = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    # Mock websockets.connect
    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()

        await handler.fn(socket)

        # Verify it connected to the HMR target (24678) not the main target (3000)
        mock_connect.assert_called_once()
        args, _ = mock_connect.call_args
        target_url = args[0]
        assert target_url == "ws://127.0.0.1:24678/_nuxt/"


async def test_ssr_proxy_falls_back_to_main_target_when_hmr_missing(hotfile: Path) -> None:
    """The WS HMR proxy falls back to the main target when ``hot.hmr`` is absent."""

    # Ensure no hmr file
    hmr_path = anyio.Path(f"{hotfile}.hmr")
    if await hmr_path.exists():
        await hmr_path.unlink()

    handler = create_ssr_ws_proxy_handler(hotfile_path=hotfile)

    # Mock WebSocket
    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    # Mock websockets.connect
    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()

        await handler.fn(socket)

        # Verify it connected to the main target (3000)
        mock_connect.assert_called_once()
        args, _ = mock_connect.call_args
        target_url = args[0]
        assert target_url == "ws://localhost:3000/_nuxt/"


@pytest.mark.parametrize(
    "headers",
    [
        [(b"host", b"localhost:8000"), (b"origin", b"https://evil.example.com")],
        [(b"host", b"localhost:8000"), (b"origin", b"http://localhost:5173")],
        [(b"host", b"app.example.com"), (b"origin", b"http://app.example.com:443")],
        [(b"origin", b"http://localhost:8000")],
        [(b"host", b"localhost:8000"), (b"origin", b"null")],
        [(b"host", b"localhost:8000"), (b"origin", b"   ")],
        [(b"host", b"localhost:8000"), (b"origin", b"http://localhost:8000"), (b"origin", b"http://localhost:8000")],
        [(b"host", b"localhost:8000"), (b"host", b"localhost:8000"), (b"origin", b"http://localhost:8000")],
        [(b"host", b"localhost:8000"), (b"origin", b"javascript://localhost:8000")],
        [(b"host", b"localhost:8000"), (b"origin", b"http://localhost:8000/extra")],
        [(b"host", b"localhost:8000"), (b"origin", b"http://user@localhost:8000")],
        [(b"host", b"[::1]:8000"), (b"origin", b"http://[::1%25eth0]:8000")],
        [(b"host", b"localhost:8000"), (b"origin", b"http://localhost:99999")],
    ],
)
async def test_ssr_ws_proxy_rejects_disallowed_origin(hotfile: Path, headers: list[tuple[bytes, bytes]]) -> None:
    handler = create_ssr_ws_proxy_handler(hotfile_path=hotfile)

    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": headers}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        await handler.fn(socket)

        socket.accept.assert_not_awaited()
        mock_connect.assert_not_called()
        socket.close.assert_awaited_once_with(code=1008, reason="Origin not allowed")


@pytest.mark.parametrize(
    "headers",
    [
        [(b"host", b"localhost:8000"), (b"origin", b"http://localhost:8000")],
        [(b"host", b"app.example.com"), (b"origin", b"https://app.example.com")],
        [(b"host", b"app.example.com"), (b"origin", b"https://app.example.com:443")],
        [(b"host", b"app.example.com:443"), (b"origin", b"https://app.example.com")],
        [(b"host", b"[::1]:8000"), (b"origin", b"http://[::1]:8000")],
        [(b"host", b"[0:0::1]:8000"), (b"origin", b"http://[::1]:8000")],
        [],
    ],
)
async def test_ssr_ws_proxy_allows_matching_origin(hotfile: Path, headers: list[tuple[bytes, bytes]]) -> None:
    handler = create_ssr_ws_proxy_handler(hotfile_path=hotfile)

    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": headers}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()

        await handler.fn(socket)

        socket.accept.assert_awaited_once()
        mock_connect.assert_called_once()
