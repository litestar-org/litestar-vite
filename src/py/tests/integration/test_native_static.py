"""Integration coverage for server-neutral production static serving."""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx
import pytest
from litestar import Litestar, Request, Response
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, NotFoundException, WebSocketDisconnect
from litestar.handlers.base import BaseRouteHandler
from litestar.middleware import DefineMiddleware
from litestar.testing import TestClient
from litestar.types import ASGIApp, Message, Receive, Scope, Send

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin
from litestar_vite.plugin import StaticFilesConfig


@runtime_checkable
class _GranianStaticConfigShape(Protocol):
    """Structural provider result consumed by Granian 0.16 auto mode."""

    placement: str
    mounts: Sequence[object]


class _StaticHeaderMiddleware:
    """Mark responses that passed through the Litestar static route."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message["headers"])
                headers.append((b"x-static-middleware", b"active"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_header)


def _require_static_access(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    if connection.headers.get("x-static-access") != "allowed":
        raise NotAuthorizedException


def _handle_static_miss(_: Request[Any, Any, Any], __: NotFoundException) -> Response[str]:
    return Response("custom static miss", status_code=418)


def _build_production_plugin(
    tmp_path: Path, *, static_files_config: StaticFilesConfig | None = None
) -> tuple[VitePlugin, Path]:
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text('{"src/main.ts":{"file":"main.js"}}', encoding="utf-8")
    (bundle_dir / "main.js").write_text("console.log('native-or-asgi');", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/assets/"),
            runtime=RuntimeConfig(dev_mode=False, set_environment=False),
        ),
        static_files_config=static_files_config,
    )
    return plugin, bundle_dir


def test_litestar_fallback_serves_eligible_assets_and_misses(tmp_path: Path) -> None:
    """TestClient always sees Litestar's static route, even for native-eligible providers."""
    plugin, _ = _build_production_plugin(tmp_path)
    app = Litestar(plugins=[plugin])

    with TestClient(app) as client:
        response = client.get("/assets/main.js")
        missing = client.get("/assets/missing.js")

    assert response.status_code == 200
    assert response.text == "console.log('native-or-asgi');"
    assert missing.status_code == 404


def test_litestar_fallback_preserves_static_guard_middleware_and_errors(tmp_path: Path) -> None:
    """Native-ineligible custom route behavior remains active inside Litestar."""
    static_config = StaticFilesConfig(
        guards=[_require_static_access],
        middleware=[DefineMiddleware(_StaticHeaderMiddleware)],
        exception_handlers={NotFoundException: _handle_static_miss},
    )
    plugin, _ = _build_production_plugin(tmp_path, static_files_config=static_config)
    app = Litestar(plugins=[plugin])

    assert plugin.get_static_server_config().mounts == ()
    with TestClient(app) as client:
        denied = client.get("/assets/main.js")
        allowed = client.get("/assets/main.js", headers={"x-static-access": "allowed"})
        missing = client.get("/assets/missing.js", headers={"x-static-access": "allowed"})

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.headers["x-static-middleware"] == "active"
    assert missing.status_code == 418
    assert missing.text == "custom static miss"
    assert missing.headers["x-static-middleware"] == "active"


def test_vite_provider_matches_granian_structural_contract(tmp_path: Path) -> None:
    """The public result has the attributes Granian consumes, without a Granian import."""
    plugin, bundle_dir = _build_production_plugin(tmp_path)

    provider_method = getattr(plugin, "get_static_server_config", None)
    assert callable(provider_method)
    config = provider_method()

    assert isinstance(config, _GranianStaticConfigShape)
    # Pin the no-import consumer contract: a str-enum compares structurally against
    # the literal "native" without importing litestar_vite's StaticPlacement.
    assert config.placement == "native"
    assert len(config.mounts) == 1
    mount = config.mounts[0]
    assert getattr(mount, "route") == "/assets"
    assert Path(getattr(mount, "directory")).resolve() == bundle_dir.resolve()
    assert getattr(mount, "directory_index") is None


def test_production_static_websocket_miss_closes_cleanly(tmp_path: Path) -> None:
    """A stale HMR websocket misses the HTTP-only static route without a KeyError."""
    plugin, _ = _build_production_plugin(tmp_path)
    app = Litestar(plugins=[plugin])

    with TestClient(app) as client:
        assert client.get("/assets/vite-hmr").status_code == 404
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/assets/vite-hmr") as websocket:
                websocket.receive_text()

    assert exc_info.value.code == 1001


@pytest.mark.parametrize("server", ["uvicorn", "granian"])
def test_real_litestar_run_serves_same_static_asset(tmp_path: Path, server: str) -> None:
    """Granian auto mode serves eligible assets natively while Uvicorn uses Litestar."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text('{"src/main.ts":{"file":"main.js"}}', encoding="utf-8")
    (bundle_dir / "main.js").write_text("console.log('litestar-run-asgi');", encoding="utf-8")
    granian_import = "from litestar_granian import GranianPlugin" if server == "granian" else ""
    plugin_list = "[vite, GranianPlugin(static='auto')]" if server == "granian" else "[vite]"
    module_name = f"{server}_static_app"
    (tmp_path / f"{module_name}.py").write_text(
        "\n".join([
            "from pathlib import Path",
            "from litestar import Litestar",
            "from litestar.middleware import DefineMiddleware",
            "from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin",
            granian_import,
            "",
            "class MarkLitestarResponse:",
            "    def __init__(self, app):",
            "        self.app = app",
            "",
            "    async def __call__(self, scope, receive, send):",
            "        async def send_with_header(message):",
            "            if message['type'] == 'http.response.start':",
            "                message['headers'] = [*message['headers'], (b'x-litestar-static', b'active')]",
            "            await send(message)",
            "",
            "        await self.app(scope, receive, send_with_header)",
            "",
            "vite = VitePlugin(config=ViteConfig(",
            "    mode='template',",
            (
                f"    paths=PathConfig(root=Path({str(tmp_path)!r}), "
                f"bundle_dir=Path({str(bundle_dir)!r}), asset_url='/assets/'),"
            ),
            "    runtime=RuntimeConfig(dev_mode=False),",
            "))",
            f"app = Litestar(plugins={plugin_list}, middleware=[DefineMiddleware(MarkLitestarResponse)])",
        ]),
        encoding="utf-8",
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "litestar",
            "--app",
            f"{module_name}:app",
            "run",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10.0
        response: httpx.Response | None = None
        while time.monotonic() < deadline and process.poll() is None:
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/assets/main.js", timeout=0.5)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)

        output = process.stdout.read() if process.poll() is not None and process.stdout is not None else ""
        assert process.poll() is None, output
        assert response is not None
        assert response.status_code == 200
        assert response.text == "console.log('litestar-run-asgi');"
        assert response.headers.get("x-litestar-static") == ("active" if server == "uvicorn" else None)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
