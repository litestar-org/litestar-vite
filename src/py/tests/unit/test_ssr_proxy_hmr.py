from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litestar import WebSocket
from litestar.exceptions import WebSocketDisconnect

from litestar_vite.plugin import create_ssr_proxy_controller

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
    """Test that SSRProxyController.ws_proxy uses the HMR target from hot.hmr."""

    # Create the controller class
    ControllerClass = create_ssr_proxy_controller(hotfile_path=hotfile)
    controller = ControllerClass(owner=MagicMock())

    # Mock WebSocket
    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    # Raise WebSocketDisconnect(code=1000) to simulate client disconnect and stop the loop
    socket.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    # Mock websockets.connect
    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()

        # Call ws_proxy
        await controller.ws_proxy.fn(controller, socket)

        # Verify it connected to the HMR target (24678) not the main target (3000)
        mock_connect.assert_called_once()
        args, _ = mock_connect.call_args
        target_url = args[0]
        assert target_url == "ws://127.0.0.1:24678/_nuxt/"


async def test_ssr_proxy_falls_back_to_main_target_when_hmr_missing(hotfile: Path) -> None:
    """Test that SSRProxyController.ws_proxy falls back to main target if hot.hmr is missing."""

    # Ensure no hmr file
    hmr_path = Path(f"{hotfile}.hmr")
    if hmr_path.exists():
        hmr_path.unlink()

    # Create the controller class
    ControllerClass = create_ssr_proxy_controller(hotfile_path=hotfile)
    controller = ControllerClass(owner=MagicMock())

    # Mock WebSocket
    socket = MagicMock(spec=WebSocket)
    socket.scope = {"type": "websocket", "path": "/_nuxt/", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    # Mock websockets.connect
    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = AsyncMock()

        # Call ws_proxy
        await controller.ws_proxy.fn(controller, socket)

        # Verify it connected to the main target (3000)
        mock_connect.assert_called_once()
        args, _ = mock_connect.call_args
        target_url = args[0]
        assert target_url == "ws://localhost:3000/_nuxt/"
