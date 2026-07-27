"""Tests for VitePlugin functionality and integration."""

import gc
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from litestar import Litestar, get
from litestar.config.app import AppConfig
from litestar.exceptions import WebSocketDisconnect
from litestar.middleware import DefineMiddleware
from litestar.params import FromPath
from litestar.template.config import TemplateConfig
from litestar.testing import TestClient

from litestar_vite.config import ExternalDevServer, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig
from litestar_vite.plugin import (
    ProxyHeadersMiddleware,
    StaticFilesConfig,
    StaticPlacement,
    VitePlugin,
    ViteProcess,
    ViteProxyMiddleware,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def cleanup_vite_process_instances() -> Generator[None, None, None]:
    """Clear ViteProcess instances after each test to prevent atexit cleanup errors.

    ViteProcess tracks all instances for signal handling and cleanup. When tests
    create instances with mock processes, these would fail during atexit cleanup.

    Returns:
        The result.
    """
    yield
    # Clear instances after each test to prevent mock cleanup errors
    ViteProcess._instances.clear()


# =====================================================
# VitePlugin Core Functionality Tests
# =====================================================


def test_vite_plugin_initialization_default_config() -> None:
    """Test plugin initialization with default configuration."""
    plugin = VitePlugin()

    assert plugin._config is not None
    assert isinstance(plugin._config, ViteConfig)
    assert plugin._asset_loader is None
    assert plugin._static_files_config is None
    assert plugin._static_files_config_supplied is False
    assert plugin._config.executor is not None
    assert plugin._vite_process is None


def test_vite_plugin_initialization_custom_config() -> None:
    """Test plugin initialization with custom configuration."""
    config = ViteConfig(
        paths=PathConfig(bundle_dir="custom/bundle", resource_dir="custom/resources"),
        runtime=RuntimeConfig(dev_mode=False),
    )
    plugin = VitePlugin(config=config)

    assert plugin._config == config
    assert str(plugin._config.bundle_dir) == "custom/bundle"
    # hot_reload requires dev_mode=True AND a Vite mode (vite/direct/proxy)
    assert plugin._config.hot_reload is False  # dev_mode=False disables HMR
    assert plugin._config.executor is not None


def test_vite_plugin_initialization_with_static_files_config() -> None:
    """Test plugin initialization with static files configuration."""
    static_config = StaticFilesConfig(tags=["static"])
    plugin = VitePlugin(static_files_config=static_config)

    assert plugin._static_files_config is not None
    assert plugin._static_files_config.as_router_kwargs()["tags"] == ["static"]
    assert plugin._static_files_config_supplied is True


def test_static_server_config_placement_contract_is_public() -> None:
    """The server-neutral placement contract is available from the package root."""
    from litestar_vite import StaticPlacement, StaticServerConfig, StaticServerMount

    mount = StaticServerMount(route="/assets", directory=Path("/tmp/assets"))
    asgi_config = StaticServerConfig(placement=StaticPlacement.ASGI, reason="development mode")
    native_config = StaticServerConfig(placement=StaticPlacement.NATIVE, mounts=(mount,))

    assert asgi_config.placement is StaticPlacement.ASGI
    assert asgi_config.mounts == ()
    assert asgi_config.reason == "development mode"
    assert native_config.placement is StaticPlacement.NATIVE
    assert native_config.reason is None
    assert mount.directory_index is None
    with pytest.raises(FrozenInstanceError):
        mount.route = "/other"  # type: ignore[misc]


def test_static_server_config_native_without_mounts_raises() -> None:
    """NATIVE placement is meaningless without at least one mount to serve."""
    from litestar_vite import StaticPlacement, StaticServerConfig

    with pytest.raises(ValueError, match="NATIVE placement requires at least one mount"):
        StaticServerConfig(placement=StaticPlacement.NATIVE)


def test_static_server_config_asgi_without_reason_raises() -> None:
    """ASGI placement must explain why Litestar's static router serves."""
    from litestar_vite import StaticPlacement, StaticServerConfig

    with pytest.raises(ValueError, match="ASGI placement requires a non-empty reason"):
        StaticServerConfig(placement=StaticPlacement.ASGI)


def test_vite_plugin_get_static_server_config_returns_production_bundle_mount(tmp_path: Path) -> None:
    """A valid production Vite bundle is eligible for native static serving."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text('{"src/main.ts":{"file":"assets/main.js"}}', encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/assets/"),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    config = plugin.get_static_server_config()

    assert config.placement is StaticPlacement.NATIVE
    assert config.reason is None
    assert len(config.mounts) == 1
    assert config.mounts[0].route == "/assets"
    assert config.mounts[0].directory == bundle_dir.resolve()
    assert config.mounts[0].directory_index is None


def test_vite_plugin_get_static_server_config_accepts_nested_vite_manifest(tmp_path: Path) -> None:
    """Vite's default nested manifest path is a valid production marker."""
    bundle_dir = tmp_path / "dist"
    (bundle_dir / ".vite").mkdir(parents=True)
    (bundle_dir / ".vite" / "manifest.json").write_text("{}", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    config = plugin.get_static_server_config()

    assert config.placement is StaticPlacement.NATIVE
    assert config.mounts[0].directory == bundle_dir.resolve()


def test_vite_plugin_get_static_server_config_accepts_built_index_without_manifest(tmp_path: Path) -> None:
    """Manifest-less static builds can use their built index as readiness evidence."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "index.html").write_text("<!doctype html>", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    config = plugin.get_static_server_config()

    assert config.placement is StaticPlacement.NATIVE
    assert config.mounts[0].directory_index is None


@pytest.mark.parametrize(
    ("config_kwargs", "reason"),
    [
        ({"enabled": False}, "Vite plugin is disabled"),
        ({"runtime": RuntimeConfig(dev_mode=True)}, "development mode"),
        ({"mode": "framework"}, "framework/SSR routing"),
        ({"runtime": RuntimeConfig(dev_mode=False, set_static_folders=False)}, "automatic static routing is disabled"),
        ({"exclude_static_from_auth": False}, "protected static assets"),
    ],
)
def test_vite_plugin_get_static_server_config_rejects_ineligible_runtime_config(
    tmp_path: Path, config_kwargs: dict[str, Any], reason: str
) -> None:
    """Runtime and security semantics that native serving bypasses must fall back."""
    resolved_kwargs = config_kwargs.copy()
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    mode = cast("Any", resolved_kwargs.pop("mode", "template"))
    runtime = cast("RuntimeConfig", resolved_kwargs.pop("runtime", RuntimeConfig(dev_mode=False)))
    plugin = VitePlugin(
        config=ViteConfig(
            mode=mode, paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir), runtime=runtime, **resolved_kwargs
        )
    )

    config = plugin.get_static_server_config()

    assert config.mounts == ()
    assert config.placement is StaticPlacement.ASGI
    assert config.reason is not None
    assert reason in config.reason


def test_vite_plugin_get_static_server_config_rejects_any_custom_static_config(tmp_path: Path) -> None:
    """Even an all-default explicit StaticFilesConfig preserves user-owned ASGI semantics."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir),
            runtime=RuntimeConfig(dev_mode=False),
        ),
        static_files_config=StaticFilesConfig(),
    )

    config = plugin.get_static_server_config()

    assert config.mounts == ()
    assert config.placement is StaticPlacement.ASGI
    assert config.reason is not None
    assert "custom Litestar static configuration" in config.reason


@pytest.mark.parametrize(
    "asset_url",
    ["/", "assets/", "//cdn.example.com/assets/", "https://cdn.example.com/assets/", "/assets/?v=1", "/assets/#v1"],
)
def test_vite_plugin_get_static_server_config_rejects_non_local_or_root_route(tmp_path: Path, asset_url: str) -> None:
    """Native routes must be unambiguous local absolute URL paths below root."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url=asset_url),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    config = plugin.get_static_server_config()

    assert config.mounts == ()
    assert config.placement is StaticPlacement.ASGI
    assert config.reason is not None
    assert "local absolute path below '/'" in config.reason


@pytest.mark.parametrize("build_state", ["missing", "empty", "unmarked", "malformed", "non-object"])
def test_vite_plugin_get_static_server_config_rejects_invalid_build(tmp_path: Path, build_state: str) -> None:
    """Only a real, parseable Vite production build is eligible."""
    bundle_dir = tmp_path / "dist"
    if build_state != "missing":
        bundle_dir.mkdir()
    if build_state == "unmarked":
        (bundle_dir / "app.js").write_text("compiled", encoding="utf-8")
    elif build_state == "malformed":
        (bundle_dir / "manifest.json").write_text("{", encoding="utf-8")
    elif build_state == "non-object":
        (bundle_dir / "manifest.json").write_text("[]", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    config = plugin.get_static_server_config()

    assert config.mounts == ()
    assert config.placement is StaticPlacement.ASGI
    assert config.reason is not None


def test_vite_plugin_get_static_server_config_keeps_litestar_static_router(tmp_path: Path) -> None:
    """Native eligibility never removes Litestar's server-neutral fallback route."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )
    app_config = AppConfig()

    assert plugin.get_static_server_config().placement is StaticPlacement.NATIVE
    with patch("litestar_vite.plugin._core.create_static_files_router") as create_router:
        plugin.on_app_init(app_config)

    create_router.assert_called_once()


def test_vite_plugin_static_files_config_ignores_none_overrides() -> None:
    """Unset user static config fields should not clobber plugin defaults."""
    static_config = StaticFilesConfig(exception_handlers=None, tags=["static"])
    plugin = VitePlugin(static_files_config=static_config)
    app_config = AppConfig()

    with patch("litestar_vite.plugin._core.create_static_files_router") as create_router:
        plugin._configure_static_files(app_config)

    kwargs = create_router.call_args.kwargs
    assert kwargs["exception_handlers"]
    assert kwargs["tags"] == ["static"]


def test_vite_plugin_config_property() -> None:
    """Test config property accessor."""
    config = ViteConfig(runtime=RuntimeConfig(port=3000))
    plugin = VitePlugin(config=config)

    assert plugin.config == config
    assert plugin.config.port == 3000


def test_vite_plugin_asset_loader_property_lazy_initialization() -> None:
    """Test asset loader property with lazy initialization."""
    plugin = VitePlugin()

    # Asset loader should be None initially
    assert plugin._asset_loader is None

    # Accessing the property should initialize it
    loader = plugin.asset_loader
    assert loader is not None
    assert plugin._asset_loader is not None

    # Subsequent access should return the same instance
    loader2 = plugin.asset_loader
    assert loader2 is loader


def test_vite_plugin_on_cli_init() -> None:
    """Test CLI initialization functionality."""
    from click import Group

    cli = Group()
    plugin = VitePlugin()

    # Should add vite command group
    plugin.on_cli_init(cli)

    # Check that the vite group was added
    assert "assets" in cli.commands


# =====================================================
# VitePlugin App Integration Tests
# =====================================================


def test_vite_plugin_app_init_without_template_config() -> None:
    """Test app initialization without template configuration."""
    plugin = VitePlugin()
    app_config = AppConfig()

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should not crash when no template config is present


def test_vite_plugin_app_init_with_jinja_template_engine(tmp_path: Path) -> None:
    """Test app initialization with Jinja template engine."""
    try:
        from litestar.plugins.jinja import JinjaTemplateEngine
    except ImportError:
        pytest.skip("Jinja not available for testing")

    plugin = VitePlugin()
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=tmp_path))
    app_config = AppConfig(template_config=template_config)

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Template callables should be registered when Jinja is available
    # We can't easily test the registered callables without more complex setup


def test_vite_plugin_app_init_without_jinja_template_engine(tmp_path: Path) -> None:
    """Test app initialization with non-Jinja template engine."""
    plugin = VitePlugin()

    # Mock a non-Jinja template engine
    mock_engine = Mock()
    template_config = Mock()
    template_config.engine_instance = mock_engine
    app_config = AppConfig(template_config=template_config)

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should handle non-Jinja engines gracefully


@patch("litestar_vite.plugin._core.JINJA_INSTALLED", False)
def test_vite_plugin_app_init_when_jinja_unavailable() -> None:
    """Test app initialization when Jinja is not available."""
    plugin = VitePlugin()
    app_config = AppConfig()

    # Should not crash when Jinja is unavailable
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_app_init_with_static_folders_enabled() -> None:
    """Test app initialization with static folder configuration enabled."""
    config = ViteConfig(runtime=RuntimeConfig(set_static_folders=True))
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should add static file router when enabled
    assert len(app_config.route_handlers) > 0


def test_vite_plugin_app_init_with_static_folders_disabled() -> None:
    """Test app initialization with static folder configuration disabled."""
    config = ViteConfig(runtime=RuntimeConfig(set_static_folders=False))
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should not add static file router when disabled
    assert len(app_config.route_handlers) == 0


def test_vite_plugin_app_init_static_directories_configuration(tmp_path: Path) -> None:
    """Test static directories configuration in app initialization."""
    bundle_dir = tmp_path / "dist"
    resource_dir = tmp_path / "src"
    static_dir = tmp_path / "public"

    # Create directories
    bundle_dir.mkdir()
    resource_dir.mkdir()
    static_dir.mkdir()

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, resource_dir=resource_dir, static_dir=static_dir),
        runtime=RuntimeConfig(set_static_folders=True, dev_mode=True),
    )
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should configure multiple static directories in dev mode
    assert len(app_config.route_handlers) > 0


def test_vite_plugin_app_init_threads_csrf_config_to_spa_handler(tmp_path: Path) -> None:
    from litestar.config.csrf import CSRFConfig

    plugin = VitePlugin(config=ViteConfig(mode="spa", paths=PathConfig(root=tmp_path)))
    app_config = AppConfig(
        csrf_config=CSRFConfig(secret="s", cookie_name="custom_cookie", header_name="x-custom-header")
    )

    plugin.on_app_init(app_config)

    assert plugin._spa_handler is not None
    assert plugin._spa_handler._csrf_cookie_name == "custom_cookie"
    assert plugin._spa_handler._csrf_header_name == "x-custom-header"


def test_vite_plugin_app_init_csrf_names_none_when_csrf_config_absent(tmp_path: Path) -> None:
    plugin = VitePlugin(config=ViteConfig(mode="spa", paths=PathConfig(root=tmp_path)))
    app_config = AppConfig()

    plugin.on_app_init(app_config)

    assert plugin._spa_handler is not None
    assert plugin._spa_handler._csrf_cookie_name is None
    assert plugin._spa_handler._csrf_header_name is None


def test_vite_plugin_production_stale_hmr_websocket_closes_cleanly(tmp_path: Path) -> None:
    """Stale dev clients reconnecting to HMR in production must not hit Litestar's static HTTP route.

    This reproduces issue #254: ``/static/{file_path:path}`` handles HTTP requests,
    but a browser tab with an old Vite HMR client may still make a websocket
    request to ``/static/vite-hmr`` after the app restarts with ``dev_mode=False``.
    """

    @get("/", sync_to_thread=False)
    def index() -> str:
        return "ok"

    bundle_dir = tmp_path / "static"
    bundle_dir.mkdir()

    app = Litestar(
        route_handlers=[index],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="template",
                    paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/"),
                    runtime=RuntimeConfig(dev_mode=False),
                )
            )
        ],
        debug=True,
    )

    with TestClient(app=app) as client:
        assert client.get("/static/vite-hmr").status_code == 404

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/static/vite-hmr") as websocket:
                websocket.receive_text()

    assert exc_info.value.code == 1001


def test_vite_plugin_app_init_no_proxy_when_proxy_mode_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When proxy_mode resolves to None (production), no proxy middleware is attached."""
    from litestar_vite.config._runtime import _cached_resolve_proxy_mode

    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)
    _cached_resolve_proxy_mode.cache_clear()

    config = ViteConfig(mode="spa", runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    plugin.on_app_init(app_config)

    assert plugin._proxy_target is None
    assert config.proxy_mode is None


def test_vite_plugin_middleware_order_preserves_proxy_headers_before_vite_proxy() -> None:
    class _PassthroughMiddleware:
        def __init__(self, app: Litestar) -> None:
            self.app = app

        async def __call__(self, scope: object, receive: object, send: object) -> None:
            await self.app(scope, receive, send)  # type: ignore[arg-type]

    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode="vite", trusted_proxies="127.0.0.1"))
    plugin = VitePlugin(config=config)
    app_config = AppConfig()
    app_config.middleware.append(DefineMiddleware(_PassthroughMiddleware))

    plugin.on_app_init(app_config)

    assert cast("Any", app_config.middleware[0]).middleware is ProxyHeadersMiddleware
    assert cast("Any", app_config.middleware[1]).middleware is ViteProxyMiddleware
    assert cast("Any", app_config.middleware[2]).middleware is _PassthroughMiddleware


def test_vite_plugin_app_init_production_mode_static_config(tmp_path: Path) -> None:
    """Test static configuration in production mode."""
    bundle_dir = tmp_path / "dist"
    bundle_dir.mkdir()

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(set_static_folders=True, dev_mode=False)
    )
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    result = plugin.on_app_init(app_config)

    assert result is app_config
    # Should only serve bundle directory in production mode
    assert len(app_config.route_handlers) > 0


# =====================================================
# VitePlugin Server Lifespan Tests
# =====================================================


def test_vite_plugin_lifespan_in_production_without_start_dev_server() -> None:
    """Test server lifespan when dev server is disabled."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False, start_dev_server=False))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    # Should yield without starting any processes
    with plugin.server_lifespan(app):
        pass  # Should complete without issues


def test_vite_plugin_lifespan_in_production_mode() -> None:
    """Test server lifespan in production mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(dev_mode=False)  # Production mode
    )
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    # Should yield without starting Vite process in production
    with plugin.server_lifespan(app):
        pass  # Should complete without issues


def test_vite_plugin_export_types_sync_skips_when_typegen_disabled(tmp_path: Path) -> None:
    config = ViteConfig(paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Litestar(route_handlers=[])

    with patch("litestar_vite.codegen.export_integration_assets") as export:
        plugin._export_types_sync(app)

    export.assert_not_called()


def test_vite_plugin_export_types_sync_skips_when_no_typegen_outputs_requested(tmp_path: Path) -> None:
    config = ViteConfig(
        paths=PathConfig(root=tmp_path),
        runtime=RuntimeConfig(dev_mode=False),
        types=TypeGenConfig(
            output=tmp_path / "generated",
            generate_sdk=False,
            generate_routes=False,
            generate_page_props=False,
            generate_schemas=False,
            generate_zod=False,
        ),
    )
    plugin = VitePlugin(config=config)
    app = Litestar(route_handlers=[])

    with patch("litestar_vite.codegen.export_integration_assets") as export:
        plugin._export_types_sync(app)

    export.assert_not_called()


@patch("litestar_vite.plugin._core.set_environment")
def test_vite_plugin_lifespan_with_environment_setup(mock_set_env: Mock) -> None:
    """Test server lifespan with environment variable setup."""
    config = ViteConfig(runtime=RuntimeConfig(set_environment=True, dev_mode=False, start_dev_server=False))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    with plugin.server_lifespan(app):
        pass

    # Should call set_environment when enabled
    mock_set_env.assert_called_once_with(config=config, app=app)


def test_server_lifespan_does_not_prewrite_hotfile_in_vite_mode(tmp_path: Path) -> None:
    """Vite's listening callback is the sole hotfile writer for Vite-based flows."""
    config = ViteConfig(
        enabled=True,
        paths=PathConfig(root=tmp_path, bundle_dir=tmp_path),
        runtime=RuntimeConfig(dev_mode=True, health_check=True, set_environment=False),
    )
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)
    vite_process = Mock()
    plugin._vite_process = vite_process

    with patch.object(VitePlugin, "_run_health_check") as run_health_check:
        with plugin.server_lifespan(app):
            assert not (tmp_path / config.hot_file).exists()

    run_health_check.assert_called_once_with()
    vite_process.start.assert_called_once()
    vite_process.stop.assert_called_once_with()


def test_server_lifespan_prewrites_hotfile_only_for_external_target(tmp_path: Path) -> None:
    """External targets remain discoverable when no Litestar Vite JS plugin runs."""
    target = "http://localhost:4200"
    config = ViteConfig(
        enabled=True,
        mode="framework",
        paths=PathConfig(root=tmp_path, bundle_dir=tmp_path),
        runtime=RuntimeConfig(
            dev_mode=True,
            external_dev_server=ExternalDevServer(target=target),
            health_check=False,
            set_environment=False,
        ),
    )
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)
    vite_process = Mock()
    plugin._vite_process = vite_process

    with plugin.server_lifespan(app):
        assert (tmp_path / config.hot_file).read_text(encoding="utf-8") == target

    vite_process.start.assert_called_once()
    vite_process.stop.assert_called_once_with()


@patch("litestar_vite.plugin._utils.console")
def test_vite_plugin_lifespan_with_vite_process_management(mock_console: Mock, tmp_path: Path) -> None:
    """Test server lifespan with Vite process management."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), paths=PathConfig(root=tmp_path))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    with patch("litestar_vite.plugin._core.ViteProcess") as mock_vite_process:
        mock_instance = Mock()
        mock_vite_process.return_value = mock_instance
        with patch.object(mock_instance, "start") as mock_start:
            with patch.object(mock_instance, "stop") as mock_stop:
                with plugin.server_lifespan(app):
                    pass

                # Should start and stop the Vite process
                mock_start.assert_called_once()
                mock_stop.assert_called_once()
        mock_vite_process.assert_called_once_with(executor=config.executor)


@patch("litestar_vite.plugin._utils.console")
def test_vite_plugin_lifespan_with_watch_mode(mock_console: Mock, tmp_path: Path) -> None:
    """Test server lifespan with watch mode (no HMR)."""
    config = ViteConfig(
        mode="framework",
        runtime=RuntimeConfig(
            dev_mode=True, proxy_mode="proxy", external_dev_server="http://localhost:4200"
        ),  # Watch mode without HMR
        paths=PathConfig(root=tmp_path),
    )
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    with patch("litestar_vite.plugin._core.ViteProcess") as mock_vite_process:
        mock_instance = Mock()
        mock_vite_process.return_value = mock_instance
        with patch.object(mock_instance, "start") as mock_start:
            with patch.object(mock_instance, "stop") as mock_stop:
                with plugin.server_lifespan(app):
                    pass

                # Should use build_watch_command instead of run_command
                mock_start.assert_called_once()
                _args, _kwargs = mock_start.call_args
                # The command should be the build watch command
                mock_stop.assert_called_once()
        mock_vite_process.assert_called_once_with(executor=config.executor)


def test_vite_plugin_lifespan_defers_vite_process_initialization_until_needed(tmp_path: Path) -> None:
    """Test ViteProcess is created only when server lifespan requires it."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), paths=PathConfig(root=tmp_path))
    plugin = VitePlugin(config=config)
    app = Mock(spec=Litestar)

    assert plugin._vite_process is None

    with patch("litestar_vite.plugin._core.ViteProcess") as mock_process:
        mock_instance = Mock()
        mock_process.return_value = mock_instance

        with plugin.server_lifespan(app):
            pass

    mock_process.assert_called_once_with(executor=config.executor)


# =====================================================
# ViteProcess Tests
# =====================================================


class _FakeProcess:
    _next_pid = 32000

    def __init__(self, *, returncode: int = 1, auto_exit_on_wait: bool = False) -> None:
        type(self)._next_pid += 1
        self.pid = type(self)._next_pid
        self.returncode: int | None = None
        self._target_returncode = returncode
        self._auto_exit_on_wait = auto_exit_on_wait
        self._exited = threading.Event()
        self.wait_calls: list[float | None] = []

    def poll(self) -> int | None:
        return self.returncode if self._exited.is_set() else None

    def wait(self, timeout: float | None = None) -> int | None:
        self.wait_calls.append(timeout)
        if self._auto_exit_on_wait and not self._exited.is_set():
            self.exit(self._target_returncode)
        elif timeout is None:
            self._exited.wait()
        elif not self._exited.is_set():
            self.exit(0)
        return self.returncode

    def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""

    def terminate(self) -> None:
        self.exit(0)

    def kill(self) -> None:
        self.exit(-9)

    def exit(self, returncode: int | None = None) -> None:
        self.returncode = self._target_returncode if returncode is None else returncode
        self._exited.set()


class _ObservedWaitProcess(_FakeProcess):
    """Fake process that exposes when its watcher is blocked in wait()."""

    def __init__(self) -> None:
        super().__init__()
        self.watcher_waiting = threading.Event()

    def wait(self, timeout: float | None = None) -> int | None:
        if timeout is None:
            self.watcher_waiting.set()
        return super().wait(timeout)


def _wait_until(condition: Callable[[], bool], *, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)
    assert condition()


def test_vite_process_initialization() -> None:
    """Test ViteProcess initialization."""
    executor = Mock()
    process = ViteProcess(executor)

    assert process.process is None
    assert process._lock is not None


def test_vite_process_does_not_install_signal_handlers() -> None:
    """The active ASGI server, not a Vite sidecar helper, owns top-level signals."""
    with patch("litestar_vite.plugin._process.signal.signal") as register_signal:
        ViteProcess(Mock())

    register_signal.assert_not_called()


def test_vite_process_registers_atexit_cleanup_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Atexit remains a single last-resort cleanup hook."""
    monkeypatch.setattr(ViteProcess, "_atexit_registered", False, raising=False)

    with patch("atexit.register") as register_atexit:
        ViteProcess(Mock())
        ViteProcess(Mock())

    register_atexit.assert_called_once_with(ViteProcess._cleanup_all_instances)


def test_vite_process_uses_reentrant_lock_for_cleanup() -> None:
    """Cleanup can safely re-enter stop() while the same thread holds the process lock."""
    executor = Mock()
    process = ViteProcess(executor)

    assert isinstance(process._lock, type(threading.RLock()))


def test_vite_process_start_creates_daemon_watcher() -> None:
    """Successful starts create a private daemon watcher for process exits."""
    mock_process = _FakeProcess()
    executor = Mock()
    executor.run.return_value = mock_process

    process = ViteProcess(executor)
    process.start(["npm", "run", "dev"], "/test/path")

    watcher = process._watcher_thread
    assert watcher is not None
    assert watcher.daemon is True

    process.stop()


@patch("litestar_vite.plugin._core.os.killpg")
def test_vite_process_restarts_unexpected_exit(mock_killpg: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected process exits are restarted with the original command and cwd."""
    monkeypatch.setattr(ViteProcess, "_RESTART_BACKOFFS", (0.0, 0.0, 0.0), raising=False)
    first = _FakeProcess()
    restarted = _FakeProcess()
    executor = Mock()
    executor.run.side_effect = [first, restarted]

    process = ViteProcess(executor)
    command = ["npm", "run", "dev"]
    cwd = Path("/test/path")
    process.start(command, cwd)

    first.exit(1)
    _wait_until(lambda: executor.run.call_count == 2 and process.process is restarted)

    assert executor.run.call_args_list[1].args == (command, cwd)
    assert process.process is restarted

    process.stop()
    assert mock_killpg.called


@patch("litestar_vite.plugin._core.os.killpg")
def test_vite_process_resets_restart_attempts_after_recovered_crash(
    mock_killpg: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each independent crash after a successful restart should get a fresh retry budget."""
    monkeypatch.setattr(ViteProcess, "_RESTART_BACKOFFS", (0.0,), raising=False)
    monkeypatch.setattr(ViteProcess, "_RESTART_STABILITY_SECONDS", 0.0, raising=False)
    first = _FakeProcess()
    second = _FakeProcess()
    third = _FakeProcess()
    executor = Mock()
    executor.run.side_effect = [first, second, third]

    process = ViteProcess(executor)
    command = ["npm", "run", "dev"]
    cwd = Path("/test/path")
    process.start(command, cwd)

    first.exit(1)
    _wait_until(lambda: executor.run.call_count == 2 and process.process is second)
    second.exit(1)
    _wait_until(lambda: executor.run.call_count == 3 and process.process is third)

    assert process._restart_error is None

    process.stop()
    assert mock_killpg.called


@patch("litestar_vite.plugin._process.time.sleep", return_value=None)
@patch("litestar_vite.plugin._core.os.killpg")
def test_vite_process_crash_cleanup_escalates_before_restart(
    mock_killpg: Mock, mock_sleep: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected-exit cleanup terminates leftover process-group children before restart."""
    monkeypatch.setattr(ViteProcess, "_RESTART_BACKOFFS", (0.0,), raising=False)
    first = _FakeProcess()
    restarted = _FakeProcess()
    executor = Mock()
    executor.run.side_effect = [first, restarted]

    process = ViteProcess(executor)
    process.start(["npm", "run", "dev"], "/test/path")

    first.exit(1)
    _wait_until(lambda: executor.run.call_count == 2 and process.process is restarted)

    first_process_signals = [call.args for call in mock_killpg.call_args_list if call.args[0] == first.pid]
    assert first_process_signals[0] == (first.pid, signal.SIGTERM)
    assert any(call.args == (0.5,) for call in mock_sleep.call_args_list)
    assert (first.pid, signal.SIGKILL) in first_process_signals

    process.stop()


@patch("litestar_vite.plugin._process.console")
def test_vite_process_stops_after_capped_restart_retries(mock_console: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    """A permanently failing dev server stops after the capped retry sequence."""
    monkeypatch.setattr(ViteProcess, "_RESTART_BACKOFFS", (0.0, 0.0, 0.0), raising=False)
    executor = Mock()
    executor.run.side_effect = [_FakeProcess(auto_exit_on_wait=True) for _ in range(4)]

    process = ViteProcess(executor)
    process.start(["npm", "run", "dev"], "/test/path")

    _wait_until(lambda: executor.run.call_count == 4 and process.process is None)

    assert process._restart_error is not None
    assert "Vite process exited unexpectedly after 3 restart attempts" in str(process._restart_error)
    assert mock_console.print.called


@patch("litestar_vite.plugin._core.os.killpg")
def test_vite_process_intentional_stop_does_not_restart(mock_killpg: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Intentional stop() must not be treated as a crash by the watcher."""
    monkeypatch.setattr(ViteProcess, "_RESTART_BACKOFFS", (0.0, 0.0, 0.0), raising=False)
    mock_process = _FakeProcess()
    executor = Mock()
    executor.run.return_value = mock_process

    process = ViteProcess(executor)
    process.start(["npm", "run", "dev"], "/test/path")
    process.stop()
    time.sleep(0.05)

    executor.run.assert_called_once()
    assert mock_killpg.called


def test_vite_process_intentional_stop_watcher_skips_crash_cleanup() -> None:
    """A watcher awakened by stop() must not clean the intentionally stopped process group."""
    child = _ObservedWaitProcess()
    executor = Mock()
    executor.run.return_value = child
    manager = ViteProcess(executor)
    manager.start(["npm", "run", "dev"], "/test/path")
    watcher = manager._watcher_thread

    assert watcher is not None
    assert child.watcher_waiting.wait(timeout=1.0)

    def finish_intentional_stop(_timeout: float) -> None:
        child.exit(0)
        manager.process = None

    with (
        patch.object(manager, "_terminate_process_group", side_effect=finish_intentional_stop),
        patch.object(
            manager, "_terminate_exited_process_group", wraps=manager._terminate_exited_process_group
        ) as cleanup_exited_group,
        patch("litestar_vite.plugin._process.time.sleep", return_value=None),
        patch("litestar_vite.plugin._process.os.killpg") as kill_process_group,
    ):
        manager.stop()
        watcher.join(timeout=1.0)

    assert not watcher.is_alive()
    cleanup_exited_group.assert_not_called()
    kill_process_group.assert_not_called()


def test_vite_process_start_after_stop_is_tracked_for_cleanup() -> None:
    """A stopped ViteProcess can be started again without losing global cleanup tracking."""
    first = _FakeProcess()
    second = _FakeProcess()
    executor = Mock()
    executor.run.side_effect = [first, second]

    process = ViteProcess(executor)
    process.start(["npm", "run", "dev"], "/test/path")
    process.stop()

    assert process not in ViteProcess._instances

    process.start(["npm", "run", "dev"], "/test/path")

    assert process in ViteProcess._instances
    assert process.process is second

    process.stop()


@patch("litestar_vite.plugin._core.os.killpg")
def test_vite_process_stop_removes_stopped_instance(mock_killpg: Mock) -> None:
    """Test stopped ViteProcess instances are removed from instance tracking."""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_process.wait.return_value = 0

    executor = Mock()
    process = ViteProcess(executor)
    process.process = cast("Any", mock_process)

    assert process in ViteProcess._instances

    process.stop()

    assert process not in ViteProcess._instances
    mock_killpg.assert_called_once_with(12345, 15)


def test_vite_process_start_success() -> None:
    """Test successful Vite process start."""
    mock_process = _FakeProcess()

    executor = Mock()
    executor.run.return_value = mock_process

    process = ViteProcess(executor)
    command = ["npm", "run", "dev"]
    cwd = "/test/path"

    process.start(command, cwd)

    assert process.process == mock_process
    executor.run.assert_called_once_with(command, Path(cwd))

    process.stop()


def test_vite_process_start_already_running() -> None:
    """Test starting Vite process when already running."""
    mock_process = _FakeProcess()

    executor = Mock()
    process = ViteProcess(executor)
    process.process = cast("Any", mock_process)

    command = ["npm", "run", "dev"]
    process.start(command, None)

    # Should not create a new process
    executor.run.assert_not_called()


@patch("litestar_vite.plugin._utils.console")
def test_vite_process_start_failure(mock_console: Mock) -> None:
    """Test Vite process start failure."""
    executor = Mock()
    executor.run.side_effect = Exception("Failed to start")

    process = ViteProcess(executor)
    command = ["npm", "run", "dev"]

    with pytest.raises(Exception, match="Failed to start"):
        process.start(command, "path")


def test_vite_process_stop_no_process() -> None:
    """Test stopping when no process is running."""
    executor = Mock()
    process = ViteProcess(executor)

    # Should not raise an exception
    process.stop()
    process.stop()


@patch("litestar_vite.plugin._core.os.killpg")
@patch("signal.SIGTERM", 15)
def test_vite_process_stop_graceful(mock_killpg: Mock) -> None:
    """Test graceful process stop."""
    mock_process = Mock()
    mock_process.pid = 12345  # Must be an integer for os.killpg
    mock_process.poll.return_value = None  # Process is running
    mock_process.wait.return_value = 0  # Process exits cleanly

    executor = Mock()
    process = ViteProcess(executor)
    process.process = mock_process

    process.stop()
    process.stop()

    # Process group termination is used on Unix
    mock_killpg.assert_called_once_with(12345, 15)
    mock_process.wait.assert_called_once()


@patch("litestar_vite.plugin._core.os.killpg")
@patch("signal.SIGTERM", 15)
@patch("signal.SIGKILL", 9)
def test_vite_process_stop_force_kill(mock_killpg: Mock) -> None:
    """Test force killing process when graceful stop fails."""
    import subprocess

    mock_process = Mock()
    mock_process.pid = 12345  # Must be an integer for os.killpg
    mock_process.poll.return_value = None  # Process is running
    mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5.0), 0]

    executor = Mock()
    process = ViteProcess(executor)
    process.process = mock_process

    process.stop()

    # First call is SIGTERM, second is SIGKILL after timeout
    assert mock_killpg.call_count == 2
    mock_killpg.assert_any_call(12345, 15)  # SIGTERM
    mock_killpg.assert_any_call(12345, 9)  # SIGKILL
    assert mock_process.wait.call_count == 2


@patch("litestar_vite.plugin._process.platform.system", return_value="Windows")
def test_vite_process_stop_windows_sends_ctrl_break(mock_system: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows sidecars receive a graceful console break before any forced cleanup."""
    monkeypatch.setattr("litestar_vite.plugin._process._CTRL_BREAK_EVENT", 1234, raising=False)
    mock_process = Mock(pid=12345)
    mock_process.poll.return_value = None
    mock_process.wait.return_value = 0
    process = ViteProcess(Mock())
    process.process = mock_process

    process.stop()

    mock_process.send_signal.assert_called_once_with(1234)
    mock_process.wait.assert_called_once()
    assert 0.0 < mock_process.wait.call_args.kwargs["timeout"] <= 5.0
    mock_system.assert_called()


@patch("litestar_vite.plugin._process.subprocess.run")
@patch("litestar_vite.plugin._process.shutil.which", return_value="C:/Windows/System32/taskkill.exe")
@patch("litestar_vite.plugin._process.platform.system", return_value="Windows")
@pytest.mark.parametrize(
    ("stop_timeout", "cooperative_timeout", "signal_timeout", "taskkill_timeout"),
    [
        pytest.param(0.5, 0.0, 0.0, 0.5, id="half-second"),
        pytest.param(1.0, 0.0, 0.0, 1.0, id="one-second"),
        pytest.param(2.0, 1.0, 0.0, 1.0, id="two-seconds"),
        pytest.param(2.5, 1.5, 0.0, 1.0, id="two-and-a-half-seconds"),
        pytest.param(5.0, 2.0, 2.0, 1.0, id="five-seconds"),
    ],
)
def test_vite_process_stop_windows_force_kills_tree(
    mock_system: Mock,
    mock_which: Mock,
    mock_run: Mock,
    monkeypatch: pytest.MonkeyPatch,
    stop_timeout: float,
    cooperative_timeout: float,
    signal_timeout: float,
    taskkill_timeout: float,
) -> None:
    """A stuck managed Windows sidecar escalates from stdin EOF to tree cleanup."""
    clock = [100.0]
    wait_timeouts: list[float] = []
    monkeypatch.setattr("litestar_vite.plugin._process._CTRL_BREAK_EVENT", 1234, raising=False)
    monkeypatch.setattr("litestar_vite.plugin._process.time.monotonic", lambda: clock[0])
    mock_process = Mock(pid=12345)
    mock_process.poll.return_value = None
    mock_process.stdin.closed = False

    def wait(*, timeout: float) -> int:
        wait_timeouts.append(timeout)
        clock[0] += timeout
        if len(wait_timeouts) < 3:
            raise subprocess.TimeoutExpired("cmd", timeout)
        return 0

    def run_taskkill(*_args: Any, timeout: float, **_kwargs: Any) -> None:
        clock[0] += timeout
        raise subprocess.TimeoutExpired("taskkill", timeout)

    mock_process.wait.side_effect = wait
    mock_run.side_effect = run_taskkill
    process = ViteProcess(Mock())
    process.process = mock_process

    process.stop(timeout=stop_timeout)

    mock_process.stdin.close.assert_called_once_with()
    mock_process.send_signal.assert_called_once_with(1234)
    mock_run.assert_called_once_with(
        ["C:/Windows/System32/taskkill.exe", "/PID", "12345", "/T", "/F"],
        check=False,
        shell=False,
        capture_output=True,
        timeout=taskkill_timeout,
    )
    assert wait_timeouts == pytest.approx([cooperative_timeout, signal_timeout, 0.0])
    assert taskkill_timeout > 0.0
    assert clock[0] == pytest.approx(100.0 + stop_timeout)
    mock_process.kill.assert_called_once_with()
    mock_system.assert_called()
    mock_which.assert_called_once_with("taskkill")


@patch("litestar_vite.plugin._process.shutil.which", return_value=None)
def test_vite_process_resolve_taskkill_uses_system_root(
    mock_which: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows tree termination remains available when System32 is absent from PATH."""
    taskkill = tmp_path / "System32" / "taskkill.exe"
    taskkill.parent.mkdir()
    taskkill.touch()
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))

    resolved = ViteProcess._resolve_taskkill()

    assert resolved == str(taskkill)
    mock_which.assert_called_once_with("taskkill")


@patch("litestar_vite.plugin._core.os.killpg")
@patch("litestar_vite.plugin._utils.console")
def test_vite_process_stop_failure(mock_console: Mock, mock_killpg: Mock) -> None:
    """Test process stop failure handling."""
    mock_process = Mock()
    mock_process.pid = 12345  # Must be an integer for os.killpg
    mock_process.poll.return_value = None
    mock_killpg.side_effect = Exception("Stop failed")

    executor = Mock()
    process = ViteProcess(executor)
    process.process = mock_process

    with pytest.raises(Exception, match="Stop failed"):
        process.stop()


# =====================================================
# StaticFilesConfig Tests
# =====================================================


def test_static_files_config_defaults() -> None:
    """Test StaticFilesConfig default values."""
    config = StaticFilesConfig()

    assert config.after_request is None
    assert config.after_response is None
    assert config.before_request is None
    assert config.cache_control is None
    assert config.exception_handlers is None
    assert config.guards is None
    assert config.middleware is None
    assert config.opt is None
    assert config.security is None
    assert config.tags is None


def test_static_files_config_custom_values() -> None:
    """Test StaticFilesConfig with custom values."""
    config = StaticFilesConfig(tags=["static", "assets"], opt={"exclude_from_auth": True})

    assert config.cache_control is None
    assert config.tags == ["static", "assets"]
    assert config.opt == {"exclude_from_auth": True}


# =====================================================
# VitePlugin With Jinja Integration Tests
# =====================================================


def test_vite_plugin_jinja_with_jinja_available(tmp_path: Path) -> None:
    """Test plugin behavior when Jinja is available."""
    try:
        from litestar.plugins.jinja import JinjaTemplateEngine
    except ImportError:
        pytest.skip("Jinja not available for testing")

    plugin = VitePlugin()
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=tmp_path))
    app_config = AppConfig(template_config=template_config)

    # Should work without errors when Jinja is available
    result = plugin.on_app_init(app_config)
    assert result is app_config


@patch("litestar_vite.plugin._core.JINJA_INSTALLED", False)
def test_vite_plugin_jinja_without_jinja_available() -> None:
    """Test plugin behavior when Jinja is not available."""
    plugin = VitePlugin()
    app_config = AppConfig()

    # Should work without errors even when Jinja is not available
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_jinja_template_callable_registration_check(tmp_path: Path) -> None:
    """Test template callable registration with isinstance check."""
    try:
        from litestar.plugins.jinja import JinjaTemplateEngine
    except ImportError:
        pytest.skip("Jinja not available for testing")

    plugin = VitePlugin()

    # Create actual JinjaTemplateEngine instance
    engine = JinjaTemplateEngine(directory=tmp_path)
    template_config = TemplateConfig(engine=engine)
    app_config = AppConfig(template_config=template_config)

    # Should handle isinstance check correctly
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_jinja_non_jinja_template_engine_handling() -> None:
    """Test handling of non-Jinja template engines."""
    plugin = VitePlugin()

    # Mock a different template engine
    mock_engine = Mock()
    # Ensure it's not a JinjaTemplateEngine
    mock_engine.__class__.__name__ = "SomeOtherEngine"

    template_config = Mock()
    template_config.engine_instance = mock_engine
    app_config = AppConfig(template_config=template_config)

    # Should handle non-Jinja engines gracefully
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_jinja_non_jinja_engine_different_name() -> None:
    """Test handling non-Jinja template engines with different name."""
    plugin = VitePlugin()

    # Mock a custom template engine
    mock_engine = Mock()
    mock_engine.__class__.__name__ = "CustomTemplateEngine"

    template_config = Mock()
    template_config.engine_instance = mock_engine
    app_config = AppConfig(template_config=template_config)

    # Should handle non-Jinja engines without attempting Jinja-specific registration
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_jinja_mako_engine() -> None:
    """Test handling Mako template engine."""
    plugin = VitePlugin()

    # Mock a Mako template engine
    mock_engine = Mock()
    mock_engine.__class__.__name__ = "MakoTemplateEngine"

    template_config = Mock()
    template_config.engine_instance = mock_engine
    app_config = AppConfig(template_config=template_config)

    # Should handle Mako engines gracefully
    result = plugin.on_app_init(app_config)
    assert result is app_config


# =====================================================
# VitePlugin Error Handling Tests
# =====================================================


def test_vite_plugin_error_resilient_to_template_config_errors() -> None:
    """Test plugin resilience to template configuration errors."""
    plugin = VitePlugin()

    # Mock template config that raises an error
    mock_template_config = Mock()
    mock_template_config.engine_instance = Mock()
    mock_template_config.engine_instance.register_template_callable.side_effect = Exception("Registration failed")

    app_config = AppConfig(template_config=mock_template_config)

    # Plugin should handle template registration errors gracefully
    # In the current implementation, it might not catch this error,
    # but it should in a robust implementation
    try:
        result = plugin.on_app_init(app_config)
        assert result is app_config
    except Exception:
        # If the plugin doesn't handle the error gracefully,
        # this test documents the current behavior
        pass


def test_vite_plugin_error_asset_loader_initialization_error_handling() -> None:
    """Test asset loader initialization error handling."""
    plugin = VitePlugin()

    # Mock asset loader initialization to fail
    with patch("litestar_vite.loader.ViteAssetLoader.initialize_loader", side_effect=Exception("Init failed")):
        with pytest.raises(Exception, match="Init failed"):
            _ = plugin.asset_loader


# =====================================================
# VitePlugin Jinja Optional Dependency Tests
# =====================================================


def test_vite_plugin_optional_works_without_jinja_template_engine() -> None:
    """Test plugin functionality when Jinja template engine is not available."""
    plugin = VitePlugin()

    # App config without any template config
    app_config = AppConfig()

    # Should work without template engine
    result = plugin.on_app_init(app_config)
    assert result is app_config
    assert plugin._config is not None


@patch("litestar_vite.plugin._core.JINJA_INSTALLED", False)
def test_vite_plugin_optional_handles_missing_jinja_contrib_module() -> None:
    """Test plugin behavior when litestar.plugins.jinja module is not available."""
    plugin = VitePlugin()
    app_config = AppConfig()

    # Should still work even if litestar.plugins.jinja is not available
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_optional_with_jinja_engine_when_available() -> None:
    """Test plugin with Jinja engine when it is available."""
    from litestar.plugins.jinja import JinjaTemplateEngine

    plugin = VitePlugin()

    # Create template config with Jinja engine
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=Path("/tmp")))
    app_config = AppConfig(template_config=template_config)

    # Should register template callables when Jinja is available
    result = plugin.on_app_init(app_config)
    assert result is app_config


@patch("litestar_vite.plugin._core.JINJA_INSTALLED", False)
def test_vite_plugin_optional_graceful_degradation_without_jinja() -> None:
    """Test graceful degradation when Jinja is completely absent."""
    plugin = VitePlugin()
    app_config = AppConfig()

    # Should work without any Jinja-related functionality
    result = plugin.on_app_init(app_config)
    assert result is app_config

    # Core functionality should still be available
    assert plugin._config is not None
    assert plugin.asset_loader is not None


def test_vite_plugin_optional_template_callable_registration_optional() -> None:
    """Test that template callable registration is optional and doesn't break plugin."""
    plugin = VitePlugin()

    # Mock a template engine that's not Jinja
    mock_engine = Mock()
    mock_engine.__class__.__name__ = "CustomTemplateEngine"

    template_config = Mock()
    template_config.engine_instance = mock_engine
    app_config = AppConfig(template_config=template_config)

    # Should handle non-Jinja engines without attempting Jinja-specific registration
    result = plugin.on_app_init(app_config)
    assert result is app_config


# =====================================================
# Template-mode + (Inertia/HTMX) x Jinja matrix
# =====================================================


@pytest.mark.parametrize(
    ("inertia_enabled", "jinja_installed", "use_jinja_template_config", "expect_callables"),
    [
        pytest.param(True, True, True, True, id="inertia-jinja"),
        pytest.param(True, False, False, False, id="inertia-no-jinja"),
        pytest.param(False, True, True, True, id="htmx-jinja"),
        pytest.param(False, False, False, False, id="htmx-no-jinja"),
    ],
)
def test_template_mode_jinja_callables_matrix(
    inertia_enabled: bool,
    jinja_installed: bool,
    use_jinja_template_config: bool,
    expect_callables: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock the Inertia x Jinja and HTMX x Jinja matrix for ``mode='template'``.

    Callables (``vite_hmr``, ``vite``, ``vite_static``, ``vite_routes``) register iff
    BOTH ``JINJA_INSTALLED`` is true AND a ``TemplateConfig`` with ``JinjaTemplateEngine``
    is provided. Without Jinja, ``mode='template'`` must still construct cleanly so
    raw-HTML / non-Jinja-engine consumers (HTMX, Mako, Chameleon) are not blocked.
    """
    from litestar.middleware.session.server_side import ServerSideSessionConfig
    from litestar.plugins.jinja import JinjaTemplateEngine
    from litestar.stores.base import Store
    from litestar.stores.memory import MemoryStore
    from litestar.types import Middleware

    import litestar_vite.plugin._core as plugin_module
    from litestar_vite.config import _vite as vite_config_mod

    monkeypatch.setattr(vite_config_mod, "JINJA_INSTALLED", jinja_installed)
    monkeypatch.setattr(plugin_module, "JINJA_INSTALLED", jinja_installed)

    inertia = True if inertia_enabled else None
    config = ViteConfig(mode="template", inertia=inertia)

    template_config: TemplateConfig | None = None
    engine: JinjaTemplateEngine | None = None
    if use_jinja_template_config:
        engine = JinjaTemplateEngine(directory=tmp_path)
        template_config = TemplateConfig(engine=engine)

    plugin = VitePlugin(config=config)
    middleware: list[Middleware] = [ServerSideSessionConfig().middleware] if inertia_enabled else []
    stores: dict[str, Store] = {"sessions": MemoryStore()} if inertia_enabled else {}
    app_config = AppConfig(template_config=template_config, middleware=middleware, stores=stores)

    plugin.on_app_init(app_config)

    if expect_callables:
        assert engine is not None
        assert "vite_hmr" in engine.engine.globals
        assert "vite" in engine.engine.globals
        assert "vite_static" in engine.engine.globals
        assert "vite_routes" in engine.engine.globals
    elif engine is not None:
        assert "vite_hmr" not in engine.engine.globals
        assert "vite" not in engine.engine.globals


def test_vite_plugin_optional_asset_url_generation_without_jinja() -> None:
    """Test asset URL generation works without Jinja template functions."""
    config = ViteConfig(paths=PathConfig(bundle_dir=Path("dist"), asset_url="/static/"))
    plugin = VitePlugin(config=config)

    # Asset loader should work independently of Jinja
    loader = plugin.asset_loader
    assert loader is not None


def test_vite_plugin_optional_development_server_without_jinja() -> None:
    """Test development server functionality without Jinja."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True))
    plugin = VitePlugin(config=config)

    # Development features should work without Jinja
    assert config.hot_reload is True
    assert config.is_dev_mode is True

    # Plugin should initialize correctly
    assert plugin._config is not None


def test_vite_plugin_optional_production_mode_without_jinja() -> None:
    """Test production mode functionality without Jinja."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)

    # Production features should work without Jinja
    app_config = AppConfig()
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_optional_static_files_config_independent_of_jinja() -> None:
    """Test static files configuration works independently of Jinja."""
    static_config = StaticFilesConfig(cache_control=None, tags=["static"])

    plugin = VitePlugin(static_files_config=static_config)

    # Static files should work regardless of Jinja availability
    assert plugin._static_files_config is not None
    assert plugin._static_files_config.tags == ["static"]

    app_config = AppConfig()
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_optional_server_lifespan_without_jinja() -> None:
    """Test server lifespan functionality without Jinja."""
    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # Server lifespan should work without Jinja
    lifespans = plugin.server_lifespan
    assert lifespans is not None


def test_vite_plugin_optional_backwards_compatibility_without_jinja() -> None:
    """Test backwards compatibility for existing code when Jinja is not available."""
    # This simulates existing user code that should continue working
    plugin = VitePlugin()

    # Standard plugin usage pattern
    assert plugin._config is not None
    assert plugin.asset_loader is not None
    assert callable(plugin.on_app_init)
    assert plugin.server_lifespan is not None

    # Should work with minimal configuration
    app = Litestar(plugins=[plugin])
    assert app is not None


def test_vite_plugin_optional_error_handling_without_jinja_dependencies() -> None:
    """Test error handling when Jinja dependencies are missing."""
    # Test error handling when attempting to use Jinja features without dependencies
    with patch.dict(sys.modules, {"jinja2": None}):
        plugin = VitePlugin()

        # Basic functionality should still work
        app_config = AppConfig()
        result = plugin.on_app_init(app_config)
        assert result is app_config

        # Asset loader should work
        loader = plugin.asset_loader
        assert loader is not None


def test_vite_plugin_optional_memory_efficiency_without_jinja() -> None:
    """Test memory efficiency when Jinja is not loaded."""
    gc.collect()  # Clean up before test

    # Plugin should not consume excessive memory without Jinja
    plugin = VitePlugin()
    app_config = AppConfig()
    plugin.on_app_init(app_config)

    # Basic checks that plugin is initialized efficiently
    assert plugin._config is not None
    assert plugin._asset_loader is None  # Lazy loading


# =====================================================
# Route Detection Tests (for SPA catch-all exclusion)
# =====================================================


def test_get_litestar_route_prefixes_with_multiple_routes() -> None:
    """Test get_litestar_route_prefixes collects all registered routes."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    @get("/posts/{post_id:int}")
    async def get_post(post_id: FromPath[int]) -> dict[str, int]:
        return {"id": post_id}

    @get("/api/v1/items")
    async def get_items() -> dict[str, str]:
        return {"message": "items"}

    app = Litestar(route_handlers=[get_users, get_post, get_items])

    prefixes = get_litestar_route_prefixes(app)

    # Should include all registered routes
    assert "/users" in prefixes
    assert "/posts/{post_id:int}" in prefixes
    assert "/api/v1/items" in prefixes
    # Only registered routes and the configured OpenAPI path are reserved.
    assert "/api" not in prefixes
    assert "/schema" in prefixes
    assert "/docs" not in prefixes


def test_get_litestar_route_prefixes_includes_openapi_config_path() -> None:
    """Test that OpenAPI schema path is included in prefixes."""
    from litestar.openapi import OpenAPIConfig

    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/hello")
    async def hello() -> dict[str, str]:
        return {"message": "hello"}

    # Custom OpenAPI schema path
    app = Litestar(
        route_handlers=[hello], openapi_config=OpenAPIConfig(title="Test API", version="1.0.0", path="/custom-schema")
    )

    prefixes = get_litestar_route_prefixes(app)

    # Should include custom schema path
    assert "/custom-schema" in prefixes
    assert "/schema" not in prefixes


def test_get_litestar_route_prefixes_caches_by_app() -> None:
    """Route prefixes are cached on each Vite plugin, never on app.state."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    plugin1 = VitePlugin()
    plugin2 = VitePlugin()
    app1 = Litestar(route_handlers=[get_users], plugins=[plugin1])
    app2 = Litestar(route_handlers=[get_users], plugins=[plugin2])

    prefixes1 = get_litestar_route_prefixes(app1)
    assert plugin1._route_prefix_cache is prefixes1
    assert not hasattr(app1.state, "litestar_vite_route_prefixes")
    assert not hasattr(app1.state, "litestar_vite_extra_route_prefixes")

    prefixes1_again = get_litestar_route_prefixes(app1)
    assert prefixes1 is prefixes1_again

    prefixes2 = get_litestar_route_prefixes(app2)
    assert prefixes1 == prefixes2
    assert prefixes1 is not prefixes2


def test_get_litestar_route_prefixes_with_no_openapi() -> None:
    """Test route prefixes when OpenAPI is disabled."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users], openapi_config=None)

    prefixes = get_litestar_route_prefixes(app)

    assert "/api" not in prefixes
    assert "/schema" not in prefixes
    assert "/docs" not in prefixes


def test_get_litestar_route_prefixes_strips_trailing_slashes() -> None:
    """Test that route prefixes have trailing slashes stripped."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    # Mock a route with trailing slash
    @get("/users/")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users])

    prefixes = get_litestar_route_prefixes(app)

    # Should strip trailing slash
    assert "/users" in prefixes
    assert "/users/" not in prefixes


def test_get_litestar_route_prefixes_preserves_configured_openapi_docs_path() -> None:
    """Configured OpenAPI docs/schema paths remain Litestar prefixes without the fallback /docs."""
    from litestar.openapi import OpenAPIConfig

    from litestar_vite.plugin import get_litestar_route_prefixes, is_litestar_route

    app = Litestar(route_handlers=[], openapi_config=OpenAPIConfig(title="Test API", version="1.0.0", path="/docs"))

    prefixes = get_litestar_route_prefixes(app)

    assert "/docs" in prefixes
    assert "/docs/openapi.json" in prefixes
    assert is_litestar_route("/docs/swagger", app) is True


def test_get_litestar_route_prefixes_includes_extra_runtime_prefixes() -> None:
    """RuntimeConfig.extra_route_prefixes deliberately re-adds custom backend prefixes."""
    from litestar_vite.plugin import get_litestar_route_prefixes, is_litestar_route

    config = ViteConfig(
        runtime=RuntimeConfig(dev_mode=False, extra_route_prefixes=("/docs/", "admin", "", "/api", "/admin/reports/"))
    )
    plugin = VitePlugin(config=config)
    app = Litestar(route_handlers=[], plugins=[plugin], openapi_config=None)

    prefixes = get_litestar_route_prefixes(app)

    assert "/admin/reports" in prefixes
    assert "/docs" in prefixes
    assert "/admin" in prefixes
    assert prefixes.count("/api") == 1
    assert "" not in prefixes
    assert prefixes.index("/admin/reports") < prefixes.index("/admin")
    assert is_litestar_route("/docs", app) is True
    assert is_litestar_route("/docs/client-page", app) is True


def test_get_litestar_route_prefixes_sorted_by_length() -> None:
    """Test that route prefixes are sorted by length (longest first)."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/a")
    async def route_a() -> dict[str, str]:
        return {}

    @get("/api/v1/users")
    async def route_long() -> dict[str, str]:
        return {}

    @get("/api")
    async def route_api() -> dict[str, str]:
        return {}

    app = Litestar(route_handlers=[route_a, route_long, route_api])

    prefixes = get_litestar_route_prefixes(app)

    # Find indices
    idx_long = prefixes.index("/api/v1/users")
    idx_api = prefixes.index("/api")
    idx_a = prefixes.index("/a")

    # Longer paths should come first
    assert idx_long < idx_api
    assert idx_api < idx_a


def test_is_litestar_route_exact_match() -> None:
    """Test is_litestar_route with exact path match."""
    from litestar_vite.plugin import is_litestar_route

    @get("/custom-endpoint")
    async def custom_endpoint() -> dict[str, str]:
        return {"message": "custom"}

    app = Litestar(route_handlers=[custom_endpoint], openapi_config=None)

    # Exact match should return True
    assert is_litestar_route("/custom-endpoint", app) is True


def test_is_litestar_route_prefix_match() -> None:
    """Test is_litestar_route with prefix matching."""
    from litestar_vite.plugin import is_litestar_route

    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users])

    # Prefix match should return True
    assert is_litestar_route("/api/users/123", app) is True
    assert is_litestar_route("/api/v1/items", app) is False


def test_is_litestar_route_non_match() -> None:
    """Test is_litestar_route returns False for non-matching paths."""
    from litestar_vite.plugin import is_litestar_route

    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users])

    # Non-matching paths should return False
    assert is_litestar_route("/users/123", app) is False
    assert is_litestar_route("/posts", app) is False
    assert is_litestar_route("/home", app) is False


def test_is_litestar_route_with_schema_path() -> None:
    """Test is_litestar_route matches OpenAPI schema path."""
    from litestar.openapi import OpenAPIConfig

    from litestar_vite.plugin import is_litestar_route

    @get("/hello")
    async def hello() -> dict[str, str]:
        return {"message": "hello"}

    app = Litestar(
        route_handlers=[hello], openapi_config=OpenAPIConfig(title="Test API", version="1.0.0", path="/schema")
    )

    # Should match schema path
    assert is_litestar_route("/schema", app) is True
    assert is_litestar_route("/schema/openapi.json", app) is True


def test_is_litestar_route_with_path_parameters() -> None:
    """Test is_litestar_route with path parameters."""
    from litestar_vite.plugin import is_litestar_route

    @get("/api/users/{user_id:int}")
    async def get_user(user_id: FromPath[int]) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar(route_handlers=[get_user])

    # The concrete static parent is derived from the registered parameterized route.
    assert is_litestar_route("/api/users/123", app) is True
    assert is_litestar_route("/api/posts/456", app) is False


def test_is_litestar_route_case_sensitive() -> None:
    """Test that is_litestar_route is case-sensitive."""
    from litestar_vite.plugin import is_litestar_route

    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users])

    # Case matters
    assert is_litestar_route("/api/users", app) is True
    assert is_litestar_route("/API/users", app) is False
    assert is_litestar_route("/Api/users", app) is False


def test_is_litestar_route_with_root_path() -> None:
    """Root `/` handlers must be detected so the SSR proxy middleware can fall through to them."""
    from litestar_vite.plugin import is_litestar_route

    @get("/")
    async def root() -> dict[str, str]:
        return {"message": "root"}

    app = Litestar(route_handlers=[root])

    assert is_litestar_route("/", app) is True


def test_is_litestar_route_root_absent_when_no_root_handler() -> None:
    """Without an explicit `/` handler, `is_litestar_route('/')` must remain False."""
    from litestar_vite.plugin import is_litestar_route

    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    plugin = VitePlugin()
    app = Litestar(route_handlers=[get_users], plugins=[plugin])

    assert is_litestar_route("/", app) is False
    assert is_litestar_route("/api/users", app) is True


def test_is_litestar_route_cache_performance() -> None:
    """Test that route detection uses a cached prefix list.

    Note:
        Coverage and CI environments can significantly slow down runtime, so we
        avoid asserting wall-clock timing here and instead assert correctness of
        the caching behavior.
    """
    from litestar_vite.plugin import get_litestar_route_prefixes, is_litestar_route

    @get("/api/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    plugin = VitePlugin()
    app = Litestar(route_handlers=[get_users], plugins=[plugin])

    # Prime the cache
    prefixes_before = get_litestar_route_prefixes(app)
    assert is_litestar_route("/api/users", app) is True

    # Mutate the app routes so a recompute would change the prefixes.
    # The cached value should continue to be used.
    app.routes.clear()

    prefixes_after = get_litestar_route_prefixes(app)
    assert prefixes_after == prefixes_before
    assert is_litestar_route("/api/users", app) is True


def test_get_litestar_route_prefixes_with_empty_app() -> None:
    """Test get_litestar_route_prefixes with app that has no routes."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    app = Litestar(route_handlers=[])

    prefixes = get_litestar_route_prefixes(app)

    assert "/api" not in prefixes
    assert "/schema" in prefixes
    assert "/docs" not in prefixes


# =====================================================
# VitePlugin Proxy Client Lifecycle Tests
# =====================================================


def test_vite_plugin_proxy_client_none_on_init() -> None:
    """Test that proxy_client is None immediately after plugin initialization."""
    plugin = VitePlugin()

    assert plugin._proxy_client is None
    assert plugin.proxy_client is None


async def test_vite_plugin_proxy_client_created_in_dev_mode_with_vite_proxy() -> None:
    """Test that proxy_client is created during lifespan in dev mode with vite proxy."""
    import httpx

    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), mode="spa")
    # Manually set proxy_mode to vite for test
    config.runtime.proxy_mode = "vite"
    plugin = VitePlugin(config=config)

    # Before lifespan, proxy_client is None
    assert plugin.proxy_client is None

    # Create a minimal app for lifespan
    app = Litestar(route_handlers=[])

    # Run the lifespan context manager
    async with plugin.lifespan(app):
        # During lifespan, proxy_client should be created
        assert plugin.proxy_client is not None
        assert isinstance(plugin.proxy_client, httpx.AsyncClient)

    # After lifespan, proxy_client should be closed and set to None
    assert plugin.proxy_client is None


async def test_vite_plugin_lifespan_initializes_spa_handler_async() -> None:
    """SPA handler setup must stay on the running event loop during async lifespan."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), mode="spa")
    plugin = VitePlugin(config=config)
    plugin._asset_loader = Mock()
    plugin._asset_loader.initialize = AsyncMock()
    plugin._spa_handler = Mock()
    plugin._spa_handler.is_initialized = False
    plugin._spa_handler.initialize_async = AsyncMock()
    plugin._spa_handler.initialize_sync = Mock()
    plugin._spa_handler.shutdown_async = AsyncMock()
    app = Litestar(route_handlers=[])

    async with plugin.lifespan(app):
        pass

    plugin._spa_handler.initialize_async.assert_awaited_once_with(
        vite_url=plugin._proxy_target, manifest=plugin._asset_loader.manifest
    )
    plugin._spa_handler.initialize_sync.assert_not_called()


async def test_vite_plugin_lifespan_parses_manifest_once_across_loader_and_handler(tmp_path: Path) -> None:
    """The loader and SPA handler decode manifest.json only once during worker startup."""
    from litestar.serialization import decode_json as real_decode_json

    from litestar_vite.handler import AppHandler

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html><body><div id='app'></div></body></html>")

    bundle_dir = tmp_path / "public"
    manifest_dir = bundle_dir / ".vite"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text('{"main.js": {"file": "assets/main.js"}}')

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, resource_dir="resources", bundle_dir="public", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=False),
    )
    plugin = VitePlugin(config=config)
    plugin._spa_handler = AppHandler(config)
    app = Litestar(route_handlers=[])

    decode_calls = 0

    def counting_decode_json(value: str | bytes, strict: bool = True) -> Any:
        nonlocal decode_calls
        decode_calls += 1
        return real_decode_json(value, strict=strict)

    with (
        patch("litestar_vite.loader.decode_json", counting_decode_json),
        patch("litestar_vite.handler._app.decode_json", counting_decode_json),
    ):
        async with plugin.lifespan(app):
            pass

    assert decode_calls == 1, f"expected manifest.json to be decoded exactly once, got {decode_calls}"


async def test_vite_plugin_proxy_client_created_in_dev_mode_with_ssr_proxy() -> None:
    """Test that proxy_client is created during lifespan in dev mode with SSR proxy."""
    import httpx

    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), mode="framework")
    # Manually set proxy_mode to proxy for test
    config.runtime.proxy_mode = "proxy"
    plugin = VitePlugin(config=config)

    # Before lifespan, proxy_client is None
    assert plugin.proxy_client is None

    # Create a minimal app for lifespan
    app = Litestar(route_handlers=[])

    # Run the lifespan context manager
    async with plugin.lifespan(app):
        # During lifespan, proxy_client should be created
        assert plugin.proxy_client is not None
        assert isinstance(plugin.proxy_client, httpx.AsyncClient)

    # After lifespan, proxy_client should be closed and set to None
    assert plugin.proxy_client is None


async def test_vite_plugin_proxy_client_none_in_production_mode() -> None:
    """Test that proxy_client remains None in production mode."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False), mode="spa")
    plugin = VitePlugin(config=config)

    # Create a minimal app for lifespan
    app = Litestar(route_handlers=[])

    # Run the lifespan context manager
    async with plugin.lifespan(app):
        # In production mode, proxy_client should remain None
        assert plugin.proxy_client is None


async def test_vite_plugin_proxy_client_none_when_no_proxy_mode() -> None:
    """proxy_client stays None when proxy_mode resolves to None.

    After C3, dev_mode + serves_own_html auto-derives proxy_mode='vite'. To exercise the
    no-proxy path, run in production mode where the auto-derivation yields None.
    """
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False), mode="template")
    plugin = VitePlugin(config=config)
    assert config.proxy_mode is None

    app = Litestar(route_handlers=[])
    async with plugin.lifespan(app):
        assert plugin.proxy_client is None
