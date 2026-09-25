"""Unit tests for Inertia IPC SSR transport integration, circuit breaker fallback, and token HTML transforms."""

from pathlib import Path
from typing import Any

import pytest
from litestar import get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.testing import create_test_client

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, SPAConfig, ViteConfig
from litestar_vite.html_transform import inject_inertia_ssr_tags
from litestar_vite.inertia import InertiaPlugin
from litestar_vite.ipc import BaseIPCTransport, CircuitState, IPCError
from litestar_vite.plugin import VitePlugin


class _MockInertiaIPCTransport(BaseIPCTransport):
    """Controllable IPC transport stub for Inertia SSR tests."""

    def __init__(self, *, should_fail: bool = False, body: str = '<div id="app">IPC_SSR_CONTENT</div>') -> None:
        self.should_fail = should_fail
        self.body = body
        self.calls: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return True

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        self.calls.append(payload)
        if self.should_fail:
            msg = "simulated worker failure"
            raise IPCError(msg)
        return {"result": {"head": ["<title>IPC Title</title>"], "body": self.body}}


def test_inject_inertia_ssr_tokens_and_crlf_preservation() -> None:
    """Verify fast token-based replacement and CRLF line-ending preservation in inject_inertia_ssr_tags."""
    template_crlf = "<html>\r\n<head>\r\n<!--inertia-head-->\r\n</head>\r\n<body>\r\n<!--inertia-body-->\r\n</body>\r\n</html>"
    result = inject_inertia_ssr_tags(
        template_crlf,
        head=["<title>Page</title>", '<meta name="description" content="test">'],
        body='<div id="app">Rendered</div>',
    )
    assert "<!--inertia-head-->" not in result
    assert "<!--inertia-body-->" not in result
    assert "<title>Page</title>\r\n<meta name=\"description\" content=\"test\">" in result
    assert '<div id="app">Rendered</div>' in result
    assert "\r\n" in result

    template_directives = "<html><head>@inertiaHead</head><body>@inertia</body></html>"
    result_dir = inject_inertia_ssr_tags(template_directives, head=["<title>Dir</title>"], body='<div id="app">Body</div>')
    assert "@inertiaHead" not in result_dir
    assert "@inertia" not in result_dir
    assert "<title>Dir</title>" in result_dir
    assert '<div id="app">Body</div>' in result_dir


def test_inertia_ssr_config_validation_and_deprecation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify InertiaSSRConfig validates UDS requirements and emits deprecation warning on custom URL."""
    with pytest.warns(DeprecationWarning, match="deprecated"):
        cfg = InertiaSSRConfig(url="http://127.0.0.1:9999/render")
    assert cfg.transport == "tcp"

    monkeypatch.setattr("litestar_vite.config._inertia.os.name", "nt")
    with pytest.raises(ValueError, match="Windows"):
        InertiaSSRConfig(transport="uds", socket_path="/tmp/ssr.sock")

    monkeypatch.setattr("litestar_vite.config._inertia.os.name", "posix")
    with pytest.raises(ValueError, match="socket_path"):
        InertiaSSRConfig(transport="uds", socket_path=None)


def test_inertia_ssr_ipc_transport_and_circuit_breaker_fallback(tmp_path: Path) -> None:
    """Verify InertiaResponse uses BaseIPCTransport and trips circuit breaker on repeated failures."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head><!--inertia-head--></head><body><div id="app">SPA_FALLBACK</div></body></html>'
    )

    ssr_config = InertiaSSRConfig(
        transport="stdio",
        url=None,
        fallback_to_client=True,
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_reset_timeout=60.0,
    )
    inertia_config = InertiaConfig(root_template="index.html", ssr=ssr_config)
    vite_plugin = VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=False),
            spa=SPAConfig(app_selector="#app"),
            inertia=inertia_config,
        )
    )

    @get("/", component="Dashboard")
    async def index() -> dict[str, Any]:
        return {"user": "Ada"}

    mock_transport = _MockInertiaIPCTransport(should_fail=False)

    with create_test_client(
        route_handlers=[index],
        plugins=[vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        inertia_plugin = client.app.plugins.get(InertiaPlugin)
        inertia_plugin._ipc_transport = mock_transport

        resp_ok = client.get("/")
        assert resp_ok.status_code == 200
        assert "IPC_SSR_CONTENT" in resp_ok.text
        assert "<title>IPC Title</title>" in resp_ok.text
        assert len(mock_transport.calls) == 1
        assert mock_transport.calls[0]["method"] == "render"
        assert mock_transport.calls[0]["params"]["component"] == "Dashboard"

        mock_transport.should_fail = True
        resp_fail_1 = client.get("/")
        assert resp_fail_1.status_code == 200
        assert "IPC_SSR_CONTENT" not in resp_fail_1.text
        assert inertia_plugin.circuit_breaker is not None
        assert inertia_plugin.circuit_breaker.state == CircuitState.CLOSED

        resp_fail_2 = client.get("/")
        assert resp_fail_2.status_code == 200
        assert inertia_plugin.circuit_breaker.state == CircuitState.OPEN
        assert len(mock_transport.calls) == 3

        resp_bypassed = client.get("/")
        assert resp_bypassed.status_code == 200
        assert len(mock_transport.calls) == 3
