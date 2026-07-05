"""Tests for VitePlugin inert registration mode."""

import sys

import pytest
from litestar import Litestar, get
from litestar.config.app import AppConfig

from litestar_vite import ViteConfig, VitePlugin


def _route_paths(app: Litestar) -> set[str]:
    return {route.path for route in app.routes}


def test_plugin_enabled_false_registers_no_vite_routes() -> None:
    @get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "1"}

    baseline = Litestar(route_handlers=[ping])
    with_plugin = Litestar(route_handlers=[ping], plugins=[VitePlugin(config=ViteConfig(enabled=False))])

    assert _route_paths(with_plugin) == _route_paths(baseline)


def test_plugin_enabled_false_adds_no_middleware_or_lifespan() -> None:
    plugin = VitePlugin(config=ViteConfig(enabled=False))
    cfg = AppConfig()
    before_middleware = len(cfg.middleware)
    before_lifespan = len(cfg.lifespan)
    before_handlers = cfg.exception_handlers

    out = plugin.on_app_init(cfg)

    assert len(out.middleware) == before_middleware
    assert len(out.lifespan) == before_lifespan
    assert out.exception_handlers == before_handlers


def test_plugin_enabled_false_keeps_cli_and_config_active() -> None:
    from click import Group

    plugin = VitePlugin(config=ViteConfig(enabled=False))
    group = Group()

    plugin.on_cli_init(group)

    assert "assets" in group.commands
    assert plugin.config is not None
    assert plugin.asset_loader is not None


def test_plugin_server_lifespan_inert_yields_without_side_effects() -> None:
    plugin = VitePlugin(config=ViteConfig(enabled=False))
    app = Litestar(route_handlers=[])

    with plugin.server_lifespan(app):
        pass

    assert plugin._vite_process is None


def test_plugin_auto_inert_in_assets_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "build"])

    @get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "1"}

    baseline = Litestar(route_handlers=[ping])
    inferred = Litestar(route_handlers=[ping], plugins=[VitePlugin(config=ViteConfig())])

    assert _route_paths(inferred) == _route_paths(baseline)


def test_plugin_explicit_true_beats_assets_cli_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "build"])
    plugin = VitePlugin(config=ViteConfig(enabled=True, mode="spa"))

    out = plugin.on_app_init(AppConfig())

    assert len(out.lifespan) >= 1
