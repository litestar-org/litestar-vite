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
    tmp_path: Path,
    *,
    command: "list[str] | None" = None,
    auto_start: bool = True,
    health_check: bool = False,
    dev_mode: bool = True,
    start_dev_server: bool = False,
) -> VitePlugin:
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head></head><body><div id="app"></div></body></html>'
    )
    ssr_config = InertiaSSRConfig(command=command, auto_start=auto_start, health_check=health_check)
    return VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=dev_mode, start_dev_server=start_dev_server),
            spa=SPAConfig(app_selector="#app"),
            inertia=InertiaConfig(ssr=ssr_config),
        )
    )


def test_ssr_config_defaults_have_no_command_so_plugin_does_nothing() -> None:
    """Without a command, the plugin must not attempt to start any SSR process."""
    config = InertiaSSRConfig()
    assert config.command is None
    assert config.auto_start is True
    # health_check is opt-in (False default) so SSR starts non-blocking and Litestar
    # is ready to serve requests immediately.
    assert config.health_check is False
    assert config.health_check_timeout > 0
    assert config.cwd is None


def test_server_lifespan_starts_and_stops_ssr_process_when_command_set(tmp_path: Path) -> None:
    """server_lifespan must spawn the SSR process and stop it on shutdown."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], auto_start=True, health_check=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], plugin.config.root_dir)
            fake_process.stop.assert_not_called()
        fake_process.stop.assert_called_once()


def test_server_lifespan_owns_vite_and_ssr_once_per_invocation(tmp_path: Path) -> None:
    """A single server lifespan owns both child processes from startup through shutdown."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], auto_start=True, health_check=False, start_dev_server=True
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])
    vite_process = MagicMock(name="vite_process")
    ssr_process = MagicMock(name="ssr_process")

    with (
        patch.object(VitePlugin, "_get_vite_process", return_value=vite_process),
        patch.object(VitePlugin, "_get_ssr_process", return_value=ssr_process),
    ):
        with plugin.server_lifespan(app):
            vite_process.start.assert_called_once()
            ssr_process.start.assert_called_once()
            vite_process.stop.assert_not_called()
            ssr_process.stop.assert_not_called()

    vite_process.stop.assert_called_once()
    ssr_process.stop.assert_called_once()


def test_server_lifespan_skips_ssr_start_when_auto_start_false(tmp_path: Path) -> None:
    """auto_start=False keeps the command as documentation but does not spawn anything."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], auto_start=False, health_check=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()
    fake_process.stop.assert_not_called()


def test_server_lifespan_uses_ssr_cwd_when_set(tmp_path: Path) -> None:
    """InertiaSSRConfig.cwd overrides the default ViteConfig.root_dir."""
    custom_cwd = tmp_path / "ssr-app"
    custom_cwd.mkdir()
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["npm", "run", "start:ssr"], health_check=False)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    ssr.cwd = custom_cwd

    app = Litestar(plugins=[plugin], middleware=[_SESSION])
    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], custom_cwd)


def test_server_lifespan_runs_health_check_when_enabled(tmp_path: Path) -> None:
    """health_check=True invokes _run_ssr_health_check after starting the process."""
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["npm", "run", "start:ssr"], health_check=True)
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with (
        patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process),
        patch.object(VitePlugin, "_run_ssr_health_check") as mock_health,
    ):
        with plugin.server_lifespan(app):
            mock_health.assert_called_once()


def test_server_lifespan_starts_ssr_in_production_mode_too(tmp_path: Path) -> None:
    """SSR auto-start works in dev_mode=False (the Vite branch is skipped, SSR runs)."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], health_check=False, dev_mode=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], plugin.config.root_dir)
        fake_process.stop.assert_called_once()


def test_server_lifespan_no_ssr_process_when_inertia_disabled(tmp_path: Path) -> None:
    """No Inertia config → no SSR process even with hybrid-shaped ViteConfig."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html><body><div id='app'></div></body></html>")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=False, start_dev_server=False),
            spa=SPAConfig(app_selector="#app"),
            inertia=InertiaConfig(ssr=None),
        )
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()


def test_server_lifespan_does_not_spawn_when_command_none(tmp_path: Path) -> None:
    """Backward-compat: when the user manages the SSR Node process separately.

    InertiaSSRConfig() with no ``command`` keeps the URL contract but the plugin must not
    spawn anything. Users running ``npm run start:ssr`` in a separate terminal continue
    to work as before.
    """
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=None, health_check=False)
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()
    # Confirm SSR config is still wired (URL contract preserved for the Inertia fetcher)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    assert ssr.url == "http://127.0.0.1:13714/render"


@pytest.mark.parametrize(
    "command", [["npm", "run", "start:ssr"], ["bun", "run", "start:ssr"], ["node", "bootstrap/ssr/ssr.js"]]
)
def test_resolved_ssr_config_returns_command_intact(tmp_path: Path, command: list[str]) -> None:
    """The plugin returns the configured command verbatim — no rewriting."""
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=command, health_check=False)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    assert ssr.command == command
