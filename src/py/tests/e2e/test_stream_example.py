"""Live transport tests for the realtime stream example."""

import json
from collections.abc import Generator

import httpx
import pytest
from websockets.sync.client import connect

from .conftest import E2E_TEST_TIMEOUT, _dev_servers
from .server_manager import ExampleServer

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(E2E_TEST_TIMEOUT)]


@pytest.fixture
def stream_dev_server() -> Generator[ExampleServer, None, None]:
    """Start or reuse the stream example with the Vite dev proxy active."""
    name = "htmx-stream"
    if name in _dev_servers:
        yield _dev_servers[name]
        return
    server = ExampleServer(name)
    server.start_dev_mode()
    server.wait_until_ready(timeout=float(E2E_TEST_TIMEOUT))
    _dev_servers[name] = server
    yield server


def test_stream_example_delivers_websocket_frames(stream_dev_server: ExampleServer) -> None:
    """Receive the queue-shaped sequence over the Litestar-origin WebSocket."""
    uri = f"ws://127.0.0.1:{stream_dev_server.litestar_port}/events/ws"
    with connect(uri, open_timeout=10) as socket:
        frames = [json.loads(socket.recv(timeout=10)) for _ in range(3)]

    assert [frame["type"] for frame in frames] == ["task.progress", "ping", "task.progress"]
    assert [frame.get("sequence") for frame in frames] == [1, None, 3]


def test_stream_example_delivers_named_sse_frames(stream_dev_server: ExampleServer) -> None:
    """Receive named SSE frames while the Vite development server is active."""
    url = f"http://127.0.0.1:{stream_dev_server.litestar_port}/events/sse"
    with httpx.stream("GET", url, timeout=10) as response:
        response.raise_for_status()
        lines = [line for line in response.iter_lines() if line]

    assert lines.count("event: task.progress") == 3
    assert any('"sequence": 1' in line for line in lines)
    assert any('"sequence": 3' in line for line in lines)
