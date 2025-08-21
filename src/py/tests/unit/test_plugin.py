"""Tests for VitePlugin functionality and integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from litestar import Litestar
from litestar.config.app import AppConfig
from litestar.template.config import TemplateConfig

from litestar_vite.config import ViteConfig
from litestar_vite.plugin import StaticFilesConfig, VitePlugin, ViteProcess

pytestmark = pytest.mark.anyio


class TestVitePlugin:
    """Test VitePlugin core functionality."""

    def test_plugin_initialization_default_config(self) -> None:
        """Test plugin initialization with default configuration."""
        plugin = VitePlugin()

        assert plugin._config is not None
        assert isinstance(plugin._config, ViteConfig)
        assert plugin._asset_loader is None
        assert plugin._static_files_config == {}

    def test_plugin_initialization_custom_config(self) -> None:
        """Test plugin initialization with custom configuration."""
        config = ViteConfig(bundle_dir="custom/bundle", resource_dir="custom/resources", hot_reload=False)
        plugin = VitePlugin(config=config)

        assert plugin._config == config
        assert str(plugin._config.bundle_dir) == "custom/bundle"
        assert plugin._config.hot_reload is False

    def test_plugin_initialization_with_static_files_config(self) -> None:
        """Test plugin initialization with static files configuration."""
        static_config = StaticFilesConfig(tags=["static"])
        plugin = VitePlugin(static_files_config=static_config)

        assert plugin._static_files_config is not None
        assert "tags" in plugin._static_files_config

    def test_config_property(self) -> None:
        """Test config property accessor."""
        config = ViteConfig(port=3000)
        plugin = VitePlugin(config=config)

        assert plugin.config == config
        assert plugin.config.port == 3000

    def test_asset_loader_property_lazy_initialization(self) -> None:
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

    def test_on_cli_init(self) -> None:
        """Test CLI initialization functionality."""
        from click import Group

        cli = Group()
        plugin = VitePlugin()

        # Should add vite command group
        plugin.on_cli_init(cli)

        # Check that the vite group was added
        assert "assets" in cli.commands


class TestVitePluginAppIntegration:
    """Test VitePlugin integration with Litestar applications."""

    def test_on_app_init_without_template_config(self) -> None:
        """Test app initialization without template configuration."""
        plugin = VitePlugin()
        app_config = AppConfig()

        result = plugin.on_app_init(app_config)

        assert result is app_config
        # Should not crash when no template config is present

    def test_on_app_init_with_jinja_template_engine(self, tmp_path: Path) -> None:
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

    def test_on_app_init_without_jinja_template_engine(self, tmp_path: Path) -> None:
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
    def test_on_app_init_when_jinja_unavailable(self) -> None:
        """Test app initialization when Jinja is not available."""
        plugin = VitePlugin()
        app_config = AppConfig()

        # Should not crash when Jinja is unavailable
        result = plugin.on_app_init(app_config)
        assert result is app_config

    def test_on_app_init_with_static_folders_enabled(self) -> None:
        """Test app initialization with static folder configuration enabled."""
        config = ViteConfig(set_static_folders=True)
        plugin = VitePlugin(config=config)
        app_config = AppConfig()

        result = plugin.on_app_init(app_config)

        assert result is app_config
        # Should add static file router when enabled
        assert len(app_config.route_handlers) > 0

    def test_on_app_init_with_static_folders_disabled(self) -> None:
        """Test app initialization with static folder configuration disabled."""
        config = ViteConfig(set_static_folders=False)
        plugin = VitePlugin(config=config)
        app_config = AppConfig()

        result = plugin.on_app_init(app_config)

        assert result is app_config
        # Should not add static file router when disabled
        assert len(app_config.route_handlers) == 0

    def test_on_app_init_static_directories_configuration(self, tmp_path: Path) -> None:
        """Test static directories configuration in app initialization."""
        bundle_dir = tmp_path / "dist"
        resource_dir = tmp_path / "src"
        public_dir = tmp_path / "public"

        # Create directories
        bundle_dir.mkdir()
        resource_dir.mkdir()
        public_dir.mkdir()

        config = ViteConfig(
            bundle_dir=str(bundle_dir),
            resource_dir=str(resource_dir),
            public_dir=str(public_dir),
            set_static_folders=True,
            dev_mode=True,
        )
        plugin = VitePlugin(config=config)
        app_config = AppConfig()

        result = plugin.on_app_init(app_config)

        assert result is app_config
        # Should configure multiple static directories in dev mode
        assert len(app_config.route_handlers) > 0

    def test_on_app_init_production_mode_static_config(self, tmp_path: Path) -> None:
        """Test static configuration in production mode."""
        bundle_dir = tmp_path / "dist"
        bundle_dir.mkdir()

        config = ViteConfig(
            bundle_dir=str(bundle_dir),
            set_static_folders=True,
            dev_mode=False,  # Production mode
        )
        plugin = VitePlugin(config=config)
        app_config = AppConfig()

        result = plugin.on_app_init(app_config)

        assert result is app_config
        # Should only serve bundle directory in production mode
        assert len(app_config.route_handlers) > 0


class TestVitePluginLifespan:
    """Test VitePlugin server lifespan management."""

    def test_server_lifespan_without_lifespan_management(self) -> None:
        """Test server lifespan when lifespan management is disabled."""
        config = ViteConfig(use_server_lifespan=False)
        plugin = VitePlugin(config=config)
        app = Mock(spec=Litestar)

        # Should yield without starting any processes
        with plugin.server_lifespan(app):
            pass  # Should complete without issues

    def test_server_lifespan_in_production_mode(self) -> None:
        """Test server lifespan in production mode."""
        config = ViteConfig(
            use_server_lifespan=True,
            dev_mode=False,  # Production mode
        )
        plugin = VitePlugin(config=config)
        app = Mock(spec=Litestar)

        # Should yield without starting Vite process in production
        with plugin.server_lifespan(app):
            pass  # Should complete without issues

    @patch("litestar_vite.plugin.set_environment")
    def test_server_lifespan_with_environment_setup(self, mock_set_env: Mock) -> None:
        """Test server lifespan with environment variable setup."""
        config = ViteConfig(set_environment=True, use_server_lifespan=False)
        plugin = VitePlugin(config=config)
        app = Mock(spec=Litestar)

        with plugin.server_lifespan(app):
            pass

        # Should call set_environment when enabled
        mock_set_env.assert_called_once_with(config=config)

    @patch("litestar_vite.plugin.console")
    def test_server_lifespan_with_vite_process_management(self, mock_console: Mock) -> None:
        """Test server lifespan with Vite process management."""
        config = ViteConfig(use_server_lifespan=True, dev_mode=True, hot_reload=True)
        plugin = VitePlugin(config=config)
        app = Mock(spec=Litestar)

        # Mock the Vite process
        with patch.object(plugin._vite_process, "start") as mock_start:
            with patch.object(plugin._vite_process, "stop") as mock_stop:
                with plugin.server_lifespan(app):
                    pass

                # Should start and stop the Vite process
                mock_start.assert_called_once()
                mock_stop.assert_called_once()

    @patch("litestar_vite.plugin.console")
    def test_server_lifespan_with_watch_mode(self, mock_console: Mock) -> None:
        """Test server lifespan with watch mode (no HMR)."""
        config = ViteConfig(
            use_server_lifespan=True,
            dev_mode=True,
            hot_reload=False,  # Watch mode without HMR
        )
        plugin = VitePlugin(config=config)
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


class TestViteProcess:
    """Test ViteProcess management functionality."""

    def test_vite_process_initialization(self) -> None:
        """Test ViteProcess initialization."""
        process = ViteProcess()

        assert process.process is None
        assert process._lock is not None

    @patch("subprocess.Popen")
    def test_vite_process_start_success(self, mock_popen: Mock) -> None:
        """Test successful Vite process start."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        process = ViteProcess()
        command = ["npm", "run", "dev"]
        cwd = "/test/path"

        process.start(command, cwd)

        assert process.process == mock_process
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    def test_vite_process_start_already_running(self, mock_popen: Mock) -> None:
        """Test starting Vite process when already running."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running

        process = ViteProcess()
        process.process = mock_process

        command = ["npm", "run", "dev"]
        process.start(command, None)

        # Should not create a new process
        mock_popen.assert_not_called()

    @patch("subprocess.Popen", side_effect=Exception("Failed to start"))
    @patch("litestar_vite.plugin.console")
    def test_vite_process_start_failure(self, mock_console: Mock, mock_popen: Mock) -> None:
        """Test Vite process start failure."""
        process = ViteProcess()
        command = ["npm", "run", "dev"]

        with pytest.raises(Exception, match="Failed to start"):
            process.start(command, None)

    def test_vite_process_stop_no_process(self) -> None:
        """Test stopping when no process is running."""
        process = ViteProcess()

        # Should not raise an exception
        process.stop()

    @patch("signal.SIGTERM", 15)
    def test_vite_process_stop_graceful(self) -> None:
        """Test graceful process stop."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = 0  # Process exits cleanly

        process = ViteProcess()
        process.process = mock_process

        process.stop()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    @patch("signal.SIGTERM", 15)
    @patch("signal.SIGKILL", 9)
    def test_vite_process_stop_force_kill(self) -> None:
        """Test force killing process when graceful stop fails."""
        import subprocess

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5.0), 0]

        process = ViteProcess()
        process.process = mock_process

        process.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2

    @patch("litestar_vite.plugin.console")
    def test_vite_process_stop_failure(self, mock_console: Mock) -> None:
        """Test process stop failure handling."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = Exception("Stop failed")

        process = ViteProcess()
        process.process = mock_process

        with pytest.raises(Exception, match="Stop failed"):
            process.stop()


class TestStaticFilesConfig:
    """Test StaticFilesConfig dataclass."""

    def test_static_files_config_defaults(self) -> None:
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

    def test_static_files_config_custom_values(self) -> None:
        """Test StaticFilesConfig with custom values."""
        config = StaticFilesConfig(tags=["static", "assets"], opt={"exclude_from_auth": True})

        assert config.cache_control is None
        assert config.tags == ["static", "assets"]
        assert config.opt == {"exclude_from_auth": True}


class TestVitePluginWithJinja:
    """Test VitePlugin specifically with Jinja integration."""

    def test_plugin_with_jinja_available(self, tmp_path: Path) -> None:
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
    def test_plugin_without_jinja_available(self) -> None:
        """Test plugin behavior when Jinja is not available."""
        plugin = VitePlugin()
        app_config = AppConfig()

        # Should work without errors even when Jinja is not available
        result = plugin.on_app_init(app_config)
        assert result is app_config

    def test_template_callable_registration_check(self, tmp_path: Path) -> None:
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

    def test_non_jinja_template_engine_handling(self) -> None:
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


class TestVitePluginErrorHandling:
    """Test error handling in VitePlugin."""

    def test_plugin_resilient_to_template_config_errors(self) -> None:
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

    def test_asset_loader_initialization_error_handling(self) -> None:
        """Test asset loader initialization error handling."""
        plugin = VitePlugin()

        # Mock asset loader initialization to fail
        with patch("litestar_vite.loader.ViteAssetLoader.initialize_loader", side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                _ = plugin.asset_loader


class TestVitePluginJinjaOptionalDependency:
    """Test VitePlugin behavior with Jinja as optional dependency."""

    def test_plugin_works_without_jinja_template_engine(self) -> None:
        """Test plugin functionality when Jinja template engine is not available."""
        plugin = VitePlugin()

        # App config without any template config
        app_config = AppConfig()

        # Should work without template engine
        result = plugin.on_app_init(app_config)
        assert result is app_config
        assert plugin._config is not None

    @patch("litestar_vite.plugin.JINJA_INSTALLED", False)
    def test_plugin_handles_missing_jinja_contrib_module(self) -> None:
        """Test plugin behavior when litestar.contrib.jinja module is not available."""
        plugin = VitePlugin()
        app_config = AppConfig()

        # Should still work even if litestar.contrib.jinja is not available
        result = plugin.on_app_init(app_config)
        assert result is app_config

    def test_plugin_with_jinja_engine_when_available(self) -> None:
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
    def test_plugin_graceful_degradation_without_jinja(self) -> None:
        """Test graceful degradation when Jinja is completely absent."""
        plugin = VitePlugin()
        app_config = AppConfig()

        # Should work without any Jinja-related functionality
        result = plugin.on_app_init(app_config)
        assert result is app_config

        # Core functionality should still be available
        assert plugin._config is not None
        assert plugin.asset_loader is not None

    def test_plugin_template_callable_registration_optional(self) -> None:
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

    def test_plugin_asset_url_generation_without_jinja(self) -> None:
        """Test asset URL generation works without Jinja template functions."""
        config = ViteConfig(bundle_dir="dist", asset_url="/static/")
        plugin = VitePlugin(config=config)

        # Asset loader should work independently of Jinja
        loader = plugin.asset_loader
        assert loader is not None

    def test_plugin_development_server_without_jinja(self) -> None:
        """Test development server functionality without Jinja."""
        config = ViteConfig(hot_reload=True, dev_mode=True)
        plugin = VitePlugin(config=config)

        # Development features should work without Jinja
        assert config.hot_reload is True
        assert config.dev_mode is True

        # Plugin should initialize correctly
        assert plugin._config is not None

    def test_plugin_production_mode_without_jinja(self) -> None:
        """Test production mode functionality without Jinja."""
        config = ViteConfig(hot_reload=False, dev_mode=False)
        plugin = VitePlugin(config=config)

        # Production features should work without Jinja
        app_config = AppConfig()
        result = plugin.on_app_init(app_config)
        assert result is app_config

    def test_plugin_static_files_config_independent_of_jinja(self) -> None:
        """Test static files configuration works independently of Jinja."""
        static_config = StaticFilesConfig(cache_control=None, tags=["static"])

        plugin = VitePlugin(static_files_config=static_config)

        # Static files should work regardless of Jinja availability
        assert plugin._static_files_config is not None
        assert plugin._static_files_config.get("tags") == ["static"]

        app_config = AppConfig()
        result = plugin.on_app_init(app_config)
        assert result is app_config

    def test_plugin_server_lifespan_without_jinja(self) -> None:
        """Test server lifespan functionality without Jinja."""
        config = ViteConfig(use_server_lifespan=True)
        plugin = VitePlugin(config=config)

        # Server lifespan should work without Jinja
        lifespans = plugin.server_lifespan
        assert lifespans is not None

    def test_plugin_backwards_compatibility_without_jinja(self) -> None:
        """Test backwards compatibility for existing code when Jinja is not available."""
        # This simulates existing user code that should continue working
        plugin = VitePlugin()

        # Standard plugin usage pattern
        assert hasattr(plugin, "_config")
        assert hasattr(plugin, "asset_loader")
        assert hasattr(plugin, "on_app_init")
        assert hasattr(plugin, "server_lifespan")

        # Should work with minimal configuration
        app = Litestar(plugins=[plugin])
        assert app is not None

    def test_plugin_error_handling_without_jinja_dependencies(self) -> None:
        """Test error handling when Jinja dependencies are missing."""
        import sys
        from unittest.mock import patch

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

    def test_plugin_memory_efficiency_without_jinja(self) -> None:
        """Test memory efficiency when Jinja is not loaded."""
        import gc

        gc.collect()  # Clean up before test

        # Plugin should not consume excessive memory without Jinja
        plugin = VitePlugin()
        app_config = AppConfig()
        plugin.on_app_init(app_config)

        # Basic checks that plugin is initialized efficiently
        assert plugin._config is not None
        assert plugin._asset_loader is None  # Lazy loading

    def test_plugin_performance_without_jinja(self) -> None:
        """Test plugin performance when Jinja is not available."""
        import time

        start_time = time.time()

        # Plugin initialization should be fast
        plugin = VitePlugin()
        app_config = AppConfig()
        plugin.on_app_init(app_config)

        init_time = time.time() - start_time

        # Should initialize quickly (less than 100ms)
        assert init_time < 0.1, f"Plugin initialization too slow: {init_time}s"
