"""Unit tests for runtime-aware production SSR command resolution across executors and plugins."""

from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock

import pytest
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.testing import create_test_client

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.executor import resolve_ssr_command
from litestar_vite.fragments import FragmentEngine
from litestar_vite.inertia import InertiaPlugin
from litestar_vite.ipc import StdioIPCTransport
from litestar_vite.plugin import VitePlugin

_SESSION = CookieBackendConfig(secret=b"x" * 32).middleware


@pytest.fixture(autouse=True)
def _isolate_venv_binaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate unit tests from wheel-provisioned JS binaries installed in the host .venv."""
    monkeypatch.setattr("litestar_vite.executor.sys.executable", str(tmp_path / "_isolated_venv" / "bin" / "python"))
    monkeypatch.setattr("litestar_vite.executor.find_spec", lambda _name: None)


@pytest.mark.parametrize(
    ("executor", "expected_prefix"),
    [
        ("node", ["node"]),
        ("pnpm", ["node"]),
        ("yarn", ["node"]),
        ("bun", ["bun", "run"]),
        ("deno", ["deno", "run", "--allow-read", "--allow-env"]),
    ],
)
def test_resolve_ssr_command_by_executor(
    tmp_path: Path, executor: Literal["node", "bun", "deno", "yarn", "pnpm"], expected_prefix: list[str]
) -> None:
    """Verify resolve_ssr_command maps each executor to its native production SSR invocation."""
    config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor=executor, dev_mode=False),
        inertia=InertiaConfig(ssr=True),
    )
    expected_bundle = str(tmp_path / "resources" / "bootstrap" / "ssr" / "ssr.js")
    assert resolve_ssr_command(config) == [*expected_prefix, expected_bundle]


def test_resolve_ssr_command_honors_explicit_override(tmp_path: Path) -> None:
    """Verify resolve_ssr_command preserves an explicit InertiaSSRConfig.command override."""
    ssr_config = InertiaSSRConfig(command=["custom-ssr-binary", "--flag"])
    config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path),
        runtime=RuntimeConfig(executor="bun", dev_mode=False),
        inertia=InertiaConfig(ssr=ssr_config),
    )
    assert resolve_ssr_command(config, ssr_config) == ["custom-ssr-binary", "--flag"]


@pytest.mark.parametrize(
    ("executor", "expected_prefix"),
    [("bun", ["bun", "run"]), ("deno", ["deno", "run", "--allow-read", "--allow-env"]), ("node", ["node"])],
)
def test_vite_plugin_and_fragment_engine_use_runtime_ssr_command(
    tmp_path: Path, executor: Literal["node", "bun", "deno"], expected_prefix: list[str]
) -> None:
    """Verify VitePlugin.get_ipc_transport and FragmentEngine._get_transport use runtime-aware SSR commands."""
    config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor=executor, dev_mode=False),
        inertia=InertiaConfig(ssr=True),
    )
    expected_cmd = [*expected_prefix, str(tmp_path / "resources" / "bootstrap" / "ssr" / "ssr.js")]

    plugin = VitePlugin(config=config)
    transport = plugin.get_ipc_transport()
    assert isinstance(transport, StdioIPCTransport)
    assert transport.command == expected_cmd

    standalone_engine = FragmentEngine(config=config, asset_loader=MagicMock())
    engine_transport = standalone_engine._get_transport()
    assert isinstance(engine_transport, StdioIPCTransport)
    assert engine_transport.command == expected_cmd


def test_standalone_inertia_plugin_uses_resolve_ssr_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify InertiaPlugin registered without VitePlugin uses resolve_ssr_command."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bun.lock").write_text("")
    inertia_plugin = InertiaPlugin(config=InertiaConfig(ssr=InertiaSSRConfig(cwd=tmp_path)))

    with create_test_client(route_handlers=[], plugins=[inertia_plugin], middleware=[_SESSION]) as client:
        active_plugin = client.app.plugins.get(InertiaPlugin)
        transport = active_plugin.ipc_transport
        assert isinstance(transport, StdioIPCTransport)
        assert transport.command[:2] == ["bun", "run"]
