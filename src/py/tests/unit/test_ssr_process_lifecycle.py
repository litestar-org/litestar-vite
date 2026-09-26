"""SSR /render Node process auto-start lifecycle.

VitePlugin.server_lifespan is responsible for starting/stopping the Inertia SSR
Node process when ``InertiaSSRConfig.command`` is configured. These tests
exercise the lifecycle without actually spawning a real Node process — the
``ViteProcess`` is patched to return mocks.
"""

import io
import queue
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from litestar import Litestar
from litestar.middleware.session.client_side import CookieBackendConfig

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, SPAConfig, ViteConfig
from litestar_vite.exceptions import ViteProcessError
from litestar_vite.plugin import VitePlugin
from litestar_vite.plugin._process import ViteProcess

_SESSION = CookieBackendConfig(secret=b"x" * 32).middleware


class _BlockingStderr:
    """Controllable binary stderr stream for restart-generation tests."""

    def __init__(self) -> None:
        self._lines: queue.Queue[bytes] = queue.Queue()
        self.started = threading.Event()
        self.finished = threading.Event()

    def readline(self) -> bytes:
        self.started.set()
        line = self._lines.get(timeout=1.0)
        if not line:
            self.finished.set()
        return line

    def feed(self, line: bytes) -> None:
        self._lines.put(line)


def test_stop_closes_stdin_before_signalling(tmp_path: Path) -> None:
    """A managed sidecar gets a bounded cooperative shutdown before process-group signals."""
    process = MagicMock(name="managed_sidecar")
    process.poll.side_effect = [None, None]
    process.stdin.closed = False
    process.wait.return_value = 0
    executor = MagicMock()
    executor.run.return_value = process
    manager = ViteProcess(executor)

    with (
        patch.object(ViteProcess, "_start_watcher"),
        patch("litestar_vite.plugin._process.os.killpg") as kill_process_group,
    ):
        manager.start(["npm", "run", "dev"], tmp_path)
        manager.stop(timeout=5.0)

    process.stdin.close.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=2.0)
    kill_process_group.assert_not_called()


def test_stop_shares_one_timeout_budget_across_shutdown_stages() -> None:
    """Cooperative, signal, and forced waits consume one overall timeout."""
    clock = [100.0]
    wait_timeouts: list[float] = []
    process = MagicMock(name="managed_sidecar", pid=12345)
    process.poll.return_value = None
    process.stdin.closed = False

    def wait(*, timeout: float) -> int:
        wait_timeouts.append(timeout)
        clock[0] += timeout
        if len(wait_timeouts) < 3:
            raise subprocess.TimeoutExpired("npm", timeout)
        return 0

    process.wait.side_effect = wait
    manager = ViteProcess(MagicMock())
    manager.process = process

    with (
        patch("litestar_vite.plugin._process.time.monotonic", side_effect=lambda: clock[0]),
        patch("litestar_vite.plugin._process.os.killpg") as kill_process_group,
    ):
        manager.stop(timeout=5.0)

    assert wait_timeouts == pytest.approx([2.0, 3.0, 0.0])
    assert kill_process_group.call_args_list == [((12345, 15),), ((12345, 9),)]


def test_immediate_exit_error_captures_stderr(tmp_path: Path) -> None:
    """A sidecar that fails before startup reports its captured stderr."""
    process = MagicMock(name="failed_sidecar")
    process.poll.return_value = 1
    process.returncode = 1
    process.stderr = io.BytesIO(b"boom\n")
    process.communicate.return_value = (None, None)
    executor = MagicMock()
    executor.run.return_value = process
    manager = ViteProcess(executor)

    try:
        with pytest.raises(ViteProcessError) as exc_info:
            manager.start(["npm", "run", "dev"], tmp_path)

        assert exc_info.value.stderr is not None
        assert "boom" in exc_info.value.stderr
        process.communicate.assert_not_called()
    finally:
        manager.stop()


def test_restart_stderr_capture_excludes_stale_previous_generation() -> None:
    """A late line from an old reader cannot contaminate a restarted process error."""
    old_stderr = _BlockingStderr()
    old_process = MagicMock(name="old_sidecar")
    old_process.stderr = old_stderr
    new_process = MagicMock(name="new_sidecar")
    new_process.stderr = io.BytesIO(b"new failure\n")
    new_process.returncode = 1
    manager = ViteProcess(MagicMock())

    try:
        manager._start_stderr_drain(old_process)
        assert old_stderr.started.wait(timeout=1.0)
        manager._start_stderr_drain(new_process)

        old_stderr.feed(b"stale previous process\n")
        old_stderr.feed(b"")
        assert old_stderr.finished.wait(timeout=1.0)

        error = manager._build_immediate_exit_error(new_process, ["npm", "run", "dev"])

        assert error.stderr is not None
        assert "new failure" in error.stderr
        assert "stale previous process" not in error.stderr
    finally:
        manager.stop()


def test_running_sidecar_mirrors_stderr_to_terminal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Continuously drained sidecar stderr remains visible in the parent terminal."""
    process = MagicMock(name="running_sidecar")
    process.poll.return_value = None
    process.stderr = io.BytesIO(b"sidecar ready\n")
    process.stdin.closed = False
    process.wait.return_value = 0
    executor = MagicMock()
    executor.run.return_value = process
    manager = ViteProcess(executor)

    try:
        with patch.object(ViteProcess, "_start_watcher"):
            manager.start(["npm", "run", "dev"], tmp_path)
        stderr_thread = getattr(manager, "_stderr_thread", None)
        if stderr_thread is not None:
            stderr_thread.join(timeout=1.0)

        assert "sidecar ready" in capsys.readouterr().err
    finally:
        manager.stop()


def _build_hybrid_plugin_with_ssr(
    tmp_path: Path, *, command: list[str] | None = None, dev_mode: bool = True, start_dev_server: bool = False
) -> VitePlugin:
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir(exist_ok=True)
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head></head><body><div id="app"></div></body></html>'
    )
    ssr_config = InertiaSSRConfig(command=command)
    return VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=dev_mode, start_dev_server=start_dev_server),
            spa=SPAConfig(app_selector="#app"),
            inertia=InertiaConfig(ssr=ssr_config),
        )
    )


def test_ssr_config_defaults() -> None:
    """Verify InertiaSSRConfig defaults for timeout, circuit breaker, and command."""
    config = InertiaSSRConfig()
    assert config.command is None
    assert config.cwd is None
    assert config.timeout == 2.0
    assert config.fallback_to_client is True
    assert config.circuit_breaker_enabled is True
    assert config.circuit_breaker_failure_threshold == 3
    assert config.circuit_breaker_reset_timeout == 30.0


def test_vite_plugin_get_ipc_transport_returns_tcp_in_dev_and_stdio_in_prod(tmp_path: Path) -> None:
    """Verify VitePlugin.get_ipc_transport uses TCPStreamIPCTransport in dev and StdioIPCTransport in prod."""
    from litestar_vite.ipc import StdioIPCTransport, TCPStreamIPCTransport

    dev_plugin = _build_hybrid_plugin_with_ssr(tmp_path, dev_mode=True)
    dev_transport = dev_plugin.get_ipc_transport()
    assert isinstance(dev_transport, TCPStreamIPCTransport)
    assert dev_transport.path == "/__litestar_ssr__"

    prod_plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["node", "bootstrap/ssr/ssr.js"], dev_mode=False)
    prod_transport = prod_plugin.get_ipc_transport()
    assert isinstance(prod_transport, StdioIPCTransport)
    assert prod_transport.command == ["node", "bootstrap/ssr/ssr.js"]


def test_server_lifespan_starts_vite_process_when_start_dev_server_true(tmp_path: Path) -> None:
    """Verify server_lifespan starts and stops ViteProcess when start_dev_server is enabled."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["node", "bootstrap/ssr/ssr.js"], dev_mode=True, start_dev_server=True
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])
    vite_process = MagicMock(name="vite_process")

    with patch.object(VitePlugin, "_get_vite_process", return_value=vite_process):
        with plugin.server_lifespan(app):
            vite_process.start.assert_called_once()
            vite_process.stop.assert_not_called()

    vite_process.stop.assert_called_once()


def test_inertia_plugin_creates_stdio_transport_with_custom_cwd(tmp_path: Path) -> None:
    """Verify InertiaPlugin.lifespan configures StdioIPCTransport with InertiaSSRConfig.cwd in production."""
    from litestar.testing import create_test_client

    from litestar_vite.inertia import InertiaPlugin
    from litestar_vite.ipc import StdioIPCTransport

    custom_cwd = tmp_path / "ssr-app"
    custom_cwd.mkdir()
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["node", "bootstrap/ssr/ssr.js"], dev_mode=False)
    assert isinstance(plugin.config.inertia, InertiaConfig)
    ssr = plugin.config.inertia.ssr_config
    assert ssr is not None
    ssr.cwd = custom_cwd

    with create_test_client(route_handlers=[], plugins=[plugin], middleware=[_SESSION]) as client:
        inertia_plugin = client.app.plugins.get(InertiaPlugin)
        transport = inertia_plugin.ipc_transport
        assert isinstance(transport, StdioIPCTransport)
        assert transport.cwd == custom_cwd
        assert transport.command == ["node", "bootstrap/ssr/ssr.js"]


@pytest.mark.parametrize(
    "command", [["npm", "run", "start:ssr"], ["bun", "run", "start:ssr"], ["node", "bootstrap/ssr/ssr.js"]]
)
def test_resolved_ssr_config_returns_command_intact(tmp_path: Path, command: list[str]) -> None:
    """Verify InertiaConfig.ssr_config returns the configured command verbatim."""
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=command)
    assert isinstance(plugin.config.inertia, InertiaConfig)
    ssr = plugin.config.inertia.ssr_config
    assert ssr is not None
    assert ssr.command == command
