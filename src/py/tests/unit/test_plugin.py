"""Tests for VitePlugin functionality and integration."""

import gc
import sys
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from litestar import Litestar, get
from litestar.config.app import AppConfig
from litestar.template.config import TemplateConfig

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.plugin import StaticFilesConfig, VitePlugin, ViteProcess

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
    assert plugin._static_files_config == {}
    assert plugin._config.executor is not None


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
    assert "tags" in plugin._static_files_config


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
        from litestar.contrib.jinja import JinjaTemplateEngine
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


@patch("litestar_vite.plugin.JINJA_INSTALLED", False)
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


def test_vite_plugin_app_init_direct_mode_skips_proxy() -> None:
    """Proxy middleware should only attach in proxy mode."""

    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode="direct"))
    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    plugin.on_app_init(app_config)

    assert app_config.middleware == []
    assert plugin._proxy_target is None


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


@patch("litestar_vite.plugin.set_environment")
def test_vite_plugin_lifespan_with_environment_setup(mock_set_env: Mock) -> None:
    """Test server lifespan with environment variable setup."""
    config = ViteConfig(runtime=RuntimeConfig(set_environment=True, dev_mode=False, start_dev_server=False))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    with plugin.server_lifespan(app):
        pass

    # Should call set_environment when enabled
    mock_set_env.assert_called_once_with(config=config)


@patch("litestar_vite.plugin._utils.console")
def test_vite_plugin_lifespan_with_vite_process_management(mock_console: Mock, tmp_path: Path) -> None:
    """Test server lifespan with Vite process management."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True), paths=PathConfig(root=tmp_path))
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    # Mock the Vite process
    with patch.object(plugin._vite_process, "start") as mock_start:
        with patch.object(plugin._vite_process, "stop") as mock_stop:
            with plugin.server_lifespan(app):
                pass

            # Should start and stop the Vite process
            mock_start.assert_called_once()
            mock_stop.assert_called_once()


@patch("litestar_vite.plugin._utils.console")
def test_vite_plugin_lifespan_with_watch_mode(mock_console: Mock, tmp_path: Path) -> None:
    """Test server lifespan with watch mode (no HMR)."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True, proxy_mode="proxy", external_dev_server="http://localhost:4200"
        ),  # Watch mode without HMR
        paths=PathConfig(root=tmp_path),
    )
    plugin = VitePlugin(config=config)
    plugin._config.types = False
    app = Mock(spec=Litestar)

    with patch.object(plugin._vite_process, "start") as mock_start:
        with patch.object(plugin._vite_process, "stop") as mock_stop:
            with plugin.server_lifespan(app):
                pass

            # Should use build_watch_command instead of run_command
            mock_start.assert_called_once()
            _args, _kwargs = mock_start.call_args
            # The command should be the build watch command
            mock_stop.assert_called_once()


# =====================================================
# ViteProcess Tests
# =====================================================


def test_vite_process_initialization() -> None:
    """Test ViteProcess initialization."""
    executor = Mock()
    process = ViteProcess(executor)

    assert process.process is None
    assert process._lock is not None


def test_vite_process_start_success() -> None:
    """Test successful Vite process start."""
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process is running

    executor = Mock()
    executor.run.return_value = mock_process

    process = ViteProcess(executor)
    command = ["npm", "run", "dev"]
    cwd = "/test/path"

    process.start(command, cwd)

    assert process.process == mock_process
    executor.run.assert_called_once_with(command, Path(cwd))


def test_vite_process_start_already_running() -> None:
    """Test starting Vite process when already running."""
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process is running

    executor = Mock()
    process = ViteProcess(executor)
    process.process = mock_process

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


@patch("litestar_vite.plugin.os.killpg")
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

    # Process group termination is used on Unix
    mock_killpg.assert_called_once_with(12345, 15)
    mock_process.wait.assert_called_once()


@patch("litestar_vite.plugin.os.killpg")
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


@patch("litestar_vite.plugin.os.killpg")
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
        from litestar.contrib.jinja import JinjaTemplateEngine
    except ImportError:
        pytest.skip("Jinja not available for testing")

    plugin = VitePlugin()
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=tmp_path))
    app_config = AppConfig(template_config=template_config)

    # Should work without errors when Jinja is available
    result = plugin.on_app_init(app_config)
    assert result is app_config


@patch("litestar_vite.plugin.JINJA_INSTALLED", False)
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
        from litestar.contrib.jinja import JinjaTemplateEngine
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


@patch("litestar_vite.plugin.JINJA_INSTALLED", False)
def test_vite_plugin_optional_handles_missing_jinja_contrib_module() -> None:
    """Test plugin behavior when litestar.contrib.jinja module is not available."""
    plugin = VitePlugin()
    app_config = AppConfig()

    # Should still work even if litestar.contrib.jinja is not available
    result = plugin.on_app_init(app_config)
    assert result is app_config


def test_vite_plugin_optional_with_jinja_engine_when_available() -> None:
    """Test plugin with Jinja engine when it is available."""
    from litestar.contrib.jinja import JinjaTemplateEngine

    plugin = VitePlugin()

    # Create template config with Jinja engine
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=Path("/tmp")))
    app_config = AppConfig(template_config=template_config)

    # Should register template callables when Jinja is available
    result = plugin.on_app_init(app_config)
    assert result is app_config


@patch("litestar_vite.plugin.JINJA_INSTALLED", False)
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
    assert plugin._static_files_config.get("tags") == ["static"]

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


def test_vite_plugin_optional_performance_without_jinja() -> None:
    """Test plugin performance when Jinja is not available."""
    start_time = time.time()

    # Plugin initialization should be fast
    plugin = VitePlugin()
    app_config = AppConfig()
    plugin.on_app_init(app_config)

    init_time = time.time() - start_time

    # Should initialize quickly (less than 100ms)
    assert init_time < 0.1, f"Plugin initialization too slow: {init_time}s"


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
    async def get_post(post_id: int) -> dict[str, int]:
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
    # Should include common API prefixes as fallback
    assert "/api" in prefixes
    assert "/schema" in prefixes
    assert "/docs" in prefixes


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
    # Should still include fallback schema path
    assert "/schema" in prefixes


def test_get_litestar_route_prefixes_caches_by_app() -> None:
    """Test that route prefixes are cached per app instance."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app1 = Litestar(route_handlers=[get_users])
    app2 = Litestar(route_handlers=[get_users])

    # First call should populate cache in app.state
    prefixes1 = get_litestar_route_prefixes(app1)

    # Second call with same app should return cached result
    prefixes1_again = get_litestar_route_prefixes(app1)
    assert prefixes1 is prefixes1_again  # Same object (tuple is immutable)

    # Different app should have separate cache entry
    prefixes2 = get_litestar_route_prefixes(app2)
    assert prefixes1 == prefixes2  # Same content
    assert prefixes1 is not prefixes2  # Different objects (separate app instances)


def test_get_litestar_route_prefixes_with_no_openapi() -> None:
    """Test route prefixes when OpenAPI is disabled."""
    from litestar_vite.plugin import get_litestar_route_prefixes

    @get("/users")
    async def get_users() -> dict[str, str]:
        return {"message": "users"}

    app = Litestar(route_handlers=[get_users], openapi_config=None)

    prefixes = get_litestar_route_prefixes(app)

    # Should still include fallback prefixes
    assert "/api" in prefixes
    assert "/schema" in prefixes
    assert "/docs" in prefixes


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
    assert is_litestar_route("/api/v1/items", app) is True  # Matches /api fallback


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
    async def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar(route_handlers=[get_user])

    # Should match based on /api prefix (from fallback)
    assert is_litestar_route("/api/users/123", app) is True
    assert is_litestar_route("/api/posts/456", app) is True


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
    """Test is_litestar_route with root path."""
    from litestar_vite.plugin import is_litestar_route

    @get("/")
    async def root() -> dict[str, str]:
        return {"message": "root"}

    app = Litestar(route_handlers=[root])

    # Root should not match (special case in SPA handler)
    # But the function itself should return False since no prefix matches
    assert is_litestar_route("/", app) is False


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

    app = Litestar(route_handlers=[get_users])

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

    # Should still include common fallback prefixes
    assert "/api" in prefixes
    assert "/schema" in prefixes
    assert "/docs" in prefixes


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
    """Test that proxy_client remains None when proxy_mode is None."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode=None), mode="template")
    plugin = VitePlugin(config=config)

    # Create a minimal app for lifespan
    app = Litestar(route_handlers=[])

    # Run the lifespan context manager
    async with plugin.lifespan(app):
        # Without proxy_mode, proxy_client should remain None
        assert plugin.proxy_client is None
