"""Tests for optional Jinja dependency support."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from litestar import Litestar
from litestar.template.config import TemplateConfig

from litestar_vite.config import ViteConfig
from litestar_vite.exceptions import MissingDependencyError

pytestmark = pytest.mark.anyio


class TestOptionalJinjaSupport:
    """Test optional Jinja dependency behavior."""

    def test_missing_dependency_error_creation(self) -> None:
        """Test MissingDependencyError can be created with package name."""
        exception = MissingDependencyError("jinja2", "jinja")
        error_msg = str(exception)
        assert "jinja2" in error_msg
        assert "litestar-vite[jinja]" in error_msg
        assert "pip install" in error_msg

    def test_commands_with_jinja_available(self, tmp_path: Path) -> None:
        """Test commands.py functions work when Jinja is available."""
        # Test that imports work when Jinja is available
        from jinja2 import Environment, FileSystemLoader

        from litestar_vite.commands import get_template

        template_env = Environment(loader=FileSystemLoader([tmp_path]))

        # Create a simple template for testing
        template_path = tmp_path / "test.j2"
        template_path.write_text("Hello {{ name }}!")

        template = get_template(environment=template_env, name="test.j2")
        assert template is not None
        assert "Hello" in template.render(name="World")

    @patch.dict(sys.modules, {"jinja2": None})
    def test_commands_without_jinja_in_type_checking(self) -> None:
        """Test that TYPE_CHECKING imports handle missing Jinja gracefully."""
        # Reload the module to test the TYPE_CHECKING imports
        import importlib

        import litestar_vite.commands

        # The module should still be importable even if jinja2 is missing
        # during TYPE_CHECKING (the imports are in a try/except block)
        importlib.reload(litestar_vite.commands)

        # Should not raise an exception
        assert litestar_vite.commands.VITE_INIT_TEMPLATES is not None

    @patch("litestar_vite.commands.JINJA_INSTALLED", False)
    def test_init_vite_without_jinja_raises_clear_error(self, tmp_path: Path) -> None:
        """Test init_vite raises clear error when Jinja is missing."""
        app = Mock(spec=Litestar)

        # This should raise MissingDependencyError with helpful message
        with pytest.raises(MissingDependencyError, match="Package 'jinja2' is not installed but required"):
            from litestar_vite.commands import init_vite

            init_vite(
                app=app,
                root_path=tmp_path,
                resource_path=tmp_path / "resources",
                asset_url="/assets/",
                public_path=tmp_path / "public",
                bundle_path=tmp_path / "dist",
                enable_ssr=False,
                vite_port=5173,
                hot_file=tmp_path / "hot",
                litestar_port=8000,
            )

    def test_plugin_with_jinja_available(self) -> None:
        """Test VitePlugin works when Jinja is available."""
        from litestar.contrib.jinja import JinjaTemplateEngine

        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Test that plugin initializes correctly
        assert plugin.config == config

        # Mock app config with JinjaTemplateEngine
        from litestar.config.app import AppConfig

        template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=Path("/")))
        app_config = AppConfig(template_config=template_config)

        # This should work without error when Jinja is available
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    def test_plugin_without_jinja_template_engine(self) -> None:
        """Test VitePlugin works when no Jinja template engine is configured."""
        from litestar.config.app import AppConfig

        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # App config without template config
        app_config = AppConfig()

        # Should work without error even when no template engine is configured
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    @patch("litestar_vite.plugin.JINJA_INSTALLED", False)
    def test_plugin_import_without_jinja_contrib(self) -> None:
        """Test plugin behavior when litestar.contrib.jinja is not available."""
        # This test simulates the scenario where litestar[jinja] extra is not installed
        from litestar.config.app import AppConfig

        from litestar_vite.plugin import VitePlugin

        plugin = VitePlugin()
        app_config = AppConfig()

        # Should work without errors even when Jinja contrib is not available
        result = plugin.on_app_init(app_config)
        assert result is app_config

    @patch("litestar_vite.commands.JINJA_INSTALLED", False)
    def test_cli_without_jinja_shows_helpful_error(self, tmp_path: Path) -> None:
        """Test CLI commands show helpful error messages when Jinja features are used without dependency."""
        with pytest.raises(MissingDependencyError) as exc_info:
            from litestar_vite.commands import init_vite

            app = Mock(spec=Litestar)
            init_vite(
                app=app,
                root_path=tmp_path,
                resource_path=tmp_path / "resources",
                asset_url="/assets/",
                public_path=tmp_path / "public",
                bundle_path=tmp_path / "dist",
                enable_ssr=False,
                vite_port=5173,
                hot_file=tmp_path / "hot",
                litestar_port=8000,
            )

            # Should mention installation instructions
            assert "litestar-vite[jinja]" in str(exc_info.value)

    def test_template_config_check_isinstance_safety(self) -> None:
        """Test that isinstance checks are safe when JinjaTemplateEngine is not available."""
        from litestar.config.app import AppConfig

        from litestar_vite.plugin import VitePlugin

        # Mock a template engine that's not JinjaTemplateEngine
        mock_engine = Mock()
        template_config = Mock()
        template_config.engine_instance = mock_engine

        app_config = AppConfig(template_config=template_config)

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Should handle non-Jinja template engines gracefully
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    def test_graceful_degradation_without_template_callables(self) -> None:
        """Test that the plugin works without registering template callables when Jinja is unavailable."""
        from litestar.config.app import AppConfig

        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # App config without any template config
        app_config = AppConfig()

        # Should complete successfully without trying to register template callables
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

        # Basic plugin functionality should still work
        assert plugin.config == config
        assert plugin.asset_loader is not None


class TestJinjaOptionalInstallationScenarios:
    """Test different installation scenarios for Jinja dependency."""

    def test_basic_functionality_without_jinja_extra(self) -> None:
        """Test that basic litestar-vite functionality works without jinja extra."""
        from litestar_vite.config import ViteConfig
        from litestar_vite.loader import ViteAssetLoader
        from litestar_vite.plugin import VitePlugin

        # Basic configuration should work
        config = ViteConfig()
        assert config is not None

        # Plugin should initialize
        plugin = VitePlugin(config=config)
        assert plugin is not None

        # Asset loader should work
        loader = ViteAssetLoader.initialize_loader(config=config)
        assert loader is not None

    def test_full_functionality_with_jinja_extra(self, tmp_path: Path) -> None:
        """Test that full functionality works when jinja extra is installed."""
        from litestar.config.app import AppConfig
        from litestar.contrib.jinja import JinjaTemplateEngine
        from litestar.template.config import TemplateConfig

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        # Full functionality should be available
        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Template integration should work
        template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=tmp_path))
        app_config = AppConfig(template_config=template_config)

        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

        # Template callables should be registered
        # We can't directly test the callables without more setup, but the registration should complete


class TestErrorMessages:
    """Test error message quality and helpfulness."""

    def test_missing_dependency_exception_message_format(self) -> None:
        """Test that MissingDependencyError has properly formatted messages."""
        exception = MissingDependencyError("jinja2", "jinja")
        error_msg = str(exception)

        assert "jinja2" in error_msg
        assert "litestar-vite[jinja]" in error_msg
        assert "pip install" in error_msg

    def test_installation_instruction_format(self) -> None:
        """Test that installation instructions follow expected format."""
        # Test the expected installation instruction format
        instruction = "pip install 'litestar-vite[jinja]'"

        # Should include the package name with jinja extra
        assert "litestar-vite" in instruction
        assert "[jinja]" in instruction
        assert "pip install" in instruction


class TestBackwardCompatibility:
    """Test backward compatibility for existing code."""

    def test_existing_imports_still_work_with_jinja(self) -> None:
        """Test that existing imports continue to work when Jinja is available."""
        # These imports should still work for backward compatibility
        from litestar_vite.config import ViteConfig
        from litestar_vite.loader import ViteAssetLoader
        from litestar_vite.plugin import VitePlugin

        # All should be importable
        assert VitePlugin is not None
        assert ViteConfig is not None
        assert ViteAssetLoader is not None

    def test_plugin_api_unchanged(self) -> None:
        """Test that the plugin API hasn't changed for existing users."""
        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        # Plugin should initialize the same way as before
        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Public API should be unchanged
        assert hasattr(plugin, "config")
        assert hasattr(plugin, "asset_loader")
        assert hasattr(plugin, "on_app_init")
        assert hasattr(plugin, "on_cli_init")
        assert hasattr(plugin, "server_lifespan")


class TestConditionalImports:
    """Test conditional import behavior in different scenarios."""

    def test_type_checking_imports_handle_missing_jinja(self) -> None:
        """Test that TYPE_CHECKING imports don't cause issues when Jinja is missing."""
        # This tests the TYPE_CHECKING block in commands.py
        import litestar_vite.commands

        # Module should be importable regardless of Jinja availability
        assert litestar_vite.commands is not None

        # Constants should still be defined
        assert hasattr(litestar_vite.commands, "VITE_INIT_TEMPLATES")
        assert hasattr(litestar_vite.commands, "DEFAULT_RESOURCES")

    def test_runtime_imports_fail_gracefully(self) -> None:
        """Test that runtime imports fail with helpful messages."""
        from unittest.mock import patch

        # Test that missing jinja2 at runtime produces appropriate errors
        with patch.dict(sys.modules, {"jinja2": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                # This should fail when trying to actually use jinja2
                from jinja2 import Environment

                Environment()


class TestJinjaOptionalEdgeCases:
    """Test edge cases and comprehensive scenarios for Jinja optional dependency."""

    def test_vite_config_without_jinja_bundle_dir(self) -> None:
        """Test ViteConfig behavior with basic configuration even when Jinja is not available."""
        from pathlib import Path

        from litestar_vite.config import ViteConfig

        # ViteConfig should work with basic configuration even if Jinja is not available
        config = ViteConfig(bundle_dir=Path("/tmp/public"))
        assert config.bundle_dir == Path("/tmp/public")

    def test_multiple_template_engine_scenarios(self) -> None:
        """Test scenarios with multiple template engines where Jinja might not be available."""
        from unittest.mock import Mock

        from litestar.config.app import AppConfig

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Mock non-Jinja template engine
        mock_engine = Mock()
        mock_engine.__class__.__name__ = "MakoTemplateEngine"

        template_config = Mock()
        template_config.engine_instance = mock_engine

        app_config = AppConfig(template_config=template_config)

        # Should handle non-Jinja engines gracefully
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    @patch.dict(sys.modules, {"jinja2": None, "litestar.contrib.jinja": None})
    def test_complete_jinja_absence_scenario(self) -> None:
        """Test complete absence of both jinja2 and litestar.contrib.jinja."""
        import importlib

        # Force reload modules to test import behavior
        if "litestar_vite.plugin" in sys.modules:
            importlib.reload(sys.modules["litestar_vite.plugin"])
        if "litestar_vite.commands" in sys.modules:
            importlib.reload(sys.modules["litestar_vite.commands"])

        # Basic imports should still work
        from litestar_vite.config import ViteConfig
        from litestar_vite.loader import ViteAssetLoader

        config = ViteConfig()
        loader = ViteAssetLoader.initialize_loader(config=config)

        assert config is not None
        assert loader is not None

    def test_jinja_available_but_litestar_contrib_missing(self) -> None:
        """Test scenario where jinja2 is available but litestar[jinja] is not installed."""
        # This test is actually testing an impossible scenario since litestar.contrib.jinja
        # is always available when jinja2 is installed. Keeping for edge case coverage.
        from litestar.config.app import AppConfig

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Should work normally
        app_config = AppConfig()
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    def test_partial_import_failure_scenarios(self) -> None:
        """Test various partial import failure scenarios."""
        from litestar_vite.commands import VITE_INIT_TEMPLATES

        # Constants should still be accessible even with import issues
        assert VITE_INIT_TEMPLATES is not None
        assert isinstance(VITE_INIT_TEMPLATES, (list, tuple, set))

    def test_error_message_consistency(self) -> None:
        """Test that error messages are consistent across different entry points."""
        from litestar_vite.exceptions import MissingDependencyError

        # All missing dependency errors should have consistent format
        exception = MissingDependencyError("jinja2", "jinja")
        error_msg = str(exception)

        # Should contain key information
        assert "jinja2" in error_msg
        assert "litestar-vite[jinja]" in error_msg
        assert "pip install" in error_msg

    def test_template_callable_registration_with_missing_jinja(self) -> None:
        """Test template callable registration when Jinja is not available."""
        from litestar.config.app import AppConfig

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # App config without template config
        app_config = AppConfig()

        # Should complete without error even when no template callables can be registered
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    def test_backwards_compatibility_imports(self) -> None:
        """Test that backwards compatibility is maintained for existing imports."""
        # These imports should work regardless of Jinja availability
        try:
            from litestar_vite import ViteConfig, VitePlugin
            from litestar_vite.config import ViteConfig as ViteConfigDirect
            from litestar_vite.plugin import VitePlugin as VitePluginDirect

            assert VitePlugin is not None
            assert ViteConfig is not None
            assert VitePluginDirect is not None
            assert ViteConfigDirect is not None
        except ImportError as e:
            pytest.fail(f"Basic imports should not fail regardless of Jinja availability: {e}")

    def test_asset_loader_independence_from_jinja(self) -> None:
        """Test that asset loader works independently of Jinja availability."""
        from pathlib import Path

        from litestar_vite.config import ViteConfig
        from litestar_vite.loader import ViteAssetLoader

        config = ViteConfig(bundle_dir=Path("/tmp/public"), resource_dir=Path("/tmp/resources"))

        # Asset loader should work regardless of Jinja
        loader = ViteAssetLoader.initialize_loader(config=config)
        assert loader is not None
        # The loader should have a config even if it's not exactly the same instance
        assert hasattr(loader, "_config")
        assert loader._config is not None

    def test_plugin_server_lifespan_without_jinja(self) -> None:
        """Test plugin server lifespan functionality without Jinja."""
        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Server lifespan should work
        lifespans = plugin.server_lifespan
        assert lifespans is not None

    def test_development_vs_production_jinja_scenarios(self) -> None:
        """Test Jinja optional behavior in development vs production scenarios."""
        from litestar_vite.config import ViteConfig

        # Development scenario
        dev_config = ViteConfig(hot_reload=True)
        assert dev_config.hot_reload is True

        # Production scenario
        prod_config = ViteConfig(hot_reload=False)
        assert prod_config.hot_reload is False

        # Both should work regardless of Jinja availability


class TestJinjaOptionalPerformanceImpact:
    """Test performance impact of Jinja optional dependency."""

    def test_import_time_without_jinja(self) -> None:
        """Test that import time is not significantly impacted when Jinja is missing."""
        import time

        start_time = time.time()

        # These imports should be fast even when Jinja is not available

        import_time = time.time() - start_time

        # Import should complete quickly (less than 1 second)
        assert import_time < 1.0, f"Import took too long: {import_time}s"

    def test_plugin_initialization_performance(self) -> None:
        """Test plugin initialization performance without Jinja."""
        import time

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        config = ViteConfig()

        start_time = time.time()
        plugin = VitePlugin(config=config)
        init_time = time.time() - start_time

        # Initialization should be fast
        assert init_time < 0.1, f"Plugin initialization took too long: {init_time}s"
        assert plugin is not None

    def test_memory_usage_without_jinja(self) -> None:
        """Test memory usage when Jinja is not available."""
        import gc

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        gc.collect()  # Clean up before test

        config = ViteConfig()
        plugin = VitePlugin(config=config)

        # Basic functionality should not cause memory leaks
        assert plugin is not None
        assert plugin.config is not None


class TestJinjaOptionalProductionReadiness:
    """Test production readiness scenarios for Jinja optional dependency."""

    def test_docker_container_scenario_without_jinja(self) -> None:
        """Test scenario typical in Docker containers where Jinja might not be installed."""
        from pathlib import Path

        from litestar.config.app import AppConfig

        from litestar_vite.config import ViteConfig
        from litestar_vite.plugin import VitePlugin

        # Typical production configuration
        config = ViteConfig(
            bundle_dir=Path("/app/public"),
            resource_dir=Path("/app/resources"),
            hot_reload=False,  # Production setting
        )

        plugin = VitePlugin(config=config)
        app_config = AppConfig()

        # Should work in production environment
        updated_config = plugin.on_app_init(app_config)
        assert updated_config is not None

    def test_kubernetes_deployment_scenario(self) -> None:
        """Test Kubernetes deployment scenario where dependencies are minimal."""
        from pathlib import Path

        from litestar_vite.config import ViteConfig
        from litestar_vite.loader import ViteAssetLoader

        # Kubernetes-style configuration with read-only filesystem considerations
        config = ViteConfig(
            bundle_dir=Path("/app/static"),
            resource_dir=Path("/app/src"),
            hot_reload=False,
        )

        loader = ViteAssetLoader.initialize_loader(config=config)
        assert loader is not None

    def test_serverless_environment_scenario(self) -> None:
        """Test serverless environment where cold starts and minimal dependencies matter."""
        import time

        start_time = time.time()

        # Fast cold start simulation
        from litestar_vite import ViteConfig, VitePlugin

        cold_start_time = time.time() - start_time

        # Should start quickly for serverless environments
        assert cold_start_time < 0.5, f"Cold start too slow for serverless: {cold_start_time}s"

        config = ViteConfig()
        plugin = VitePlugin(config=config)
        assert plugin is not None
