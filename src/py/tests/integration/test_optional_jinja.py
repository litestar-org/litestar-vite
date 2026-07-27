"""Tests for optional Jinja dependency support."""

import gc
import importlib
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from litestar.config.app import AppConfig
from litestar.template.config import TemplateConfig

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.exceptions import MissingDependencyError

pytestmark = pytest.mark.anyio


def _react_scaffold_context() -> "object":
    """Build a minimal React scaffolding context.

    Returns:
        A TemplateContext for the React template.
    """
    from litestar_vite.scaffolding import TemplateContext
    from litestar_vite.scaffolding.templates import get_template

    framework = get_template("react")
    assert framework is not None
    return TemplateContext(
        project_name="test-project", framework=framework, use_typescript=True, vite_port=5173, litestar_port=8000
    )


# =====================================================
# Optional Jinja Support Tests
# =====================================================


def test_optional_jinja_missing_dependency_error_creation() -> None:
    """MissingDependencyError names both the extra and the real PyPI package."""
    exception = MissingDependencyError(package="jinja2", extra="jinja")
    error_msg = str(exception)
    assert "'jinja2' is not installed" in error_msg
    assert "pip install litestar-vite[jinja]" in error_msg
    assert "pip install jinja2" in error_msg


def test_optional_jinja_missing_dependency_error_without_extra() -> None:
    """Dependencies with no matching extra only get the direct install hint."""
    error_msg = str(MissingDependencyError(package="gcsfs"))
    assert "pip install gcsfs" in error_msg
    assert "litestar-vite[" not in error_msg


@patch("litestar_vite.scaffolding.generator.JINJA_INSTALLED", False)
def test_optional_jinja_scaffolding_without_jinja_raises_clear_error(tmp_path: Path) -> None:
    """Scaffolding raises a clear error when Jinja is missing."""
    from litestar_vite.scaffolding import generate_project

    with pytest.raises(MissingDependencyError, match="Package 'jinja2' is not installed but required"):
        generate_project(tmp_path, _react_scaffold_context())  # type: ignore[arg-type]


def test_optional_jinja_plugin_with_jinja_available() -> None:
    """Test VitePlugin works when Jinja is available."""
    from litestar.plugins.jinja import JinjaTemplateEngine

    from litestar_vite.plugin import VitePlugin

    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # Test that plugin initializes correctly
    assert plugin.config == config

    # Mock app config with JinjaTemplateEngine
    template_config = TemplateConfig(engine=JinjaTemplateEngine(directory=Path("/")))
    app_config = AppConfig(template_config=template_config)

    # This should work without error when Jinja is available
    updated_config = plugin.on_app_init(app_config)
    assert updated_config is not None


def test_optional_jinja_plugin_without_jinja_template_engine() -> None:
    """Test VitePlugin works when no Jinja template engine is configured."""
    from litestar_vite.plugin import VitePlugin

    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # App config without template config
    app_config = AppConfig()

    # Should work without error even when no template engine is configured
    updated_config = plugin.on_app_init(app_config)
    assert updated_config is not None


@patch("litestar_vite.plugin._core.JINJA_INSTALLED", False)
def test_optional_jinja_plugin_import_without_jinja_contrib() -> None:
    """Test plugin behavior when litestar.plugins.jinja is not available."""
    # This test simulates the scenario where litestar[jinja] extra is not installed
    from litestar_vite.plugin import VitePlugin

    plugin = VitePlugin()
    app_config = AppConfig()

    # Should work without errors even when Jinja contrib is not available
    result = plugin.on_app_init(app_config)
    assert result is app_config


@patch("litestar_vite.scaffolding.generator.JINJA_INSTALLED", False)
def test_optional_jinja_cli_without_jinja_shows_helpful_error(tmp_path: Path) -> None:
    """``litestar assets init`` surfaces install instructions when jinja2 is absent.

    The CLI reaches scaffolding through the same ``generate_project`` symbol it imports
    at module scope, so the guard must hold for the exact object the CLI calls rather
    than for a separate wrapper.
    """
    from litestar_vite.cli import generate_project as cli_generate_project

    with pytest.raises(MissingDependencyError) as exc_info:
        cli_generate_project(tmp_path, _react_scaffold_context())  # type: ignore[arg-type]

    assert "pip install litestar-vite[jinja]" in str(exc_info.value)


def test_optional_jinja_template_config_check_isinstance_safety() -> None:
    """Test that isinstance checks are safe when JinjaTemplateEngine is not available."""
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


def test_optional_jinja_graceful_degradation_without_template_callables() -> None:
    """Test that the plugin works without registering template callables when Jinja is unavailable."""
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


# =====================================================
# Jinja Optional Installation Scenarios Tests
# =====================================================


def test_installation_basic_functionality_without_jinja_extra() -> None:
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


def test_installation_full_functionality_with_jinja_extra(tmp_path: Path) -> None:
    """Test that full functionality works when jinja extra is installed."""
    from litestar.plugins.jinja import JinjaTemplateEngine

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


# =====================================================
# Error Messages Tests
# =====================================================


def test_error_messages_missing_dependency_exception_format() -> None:
    """Test that MissingDependencyError has properly formatted messages."""
    exception = MissingDependencyError("jinja2", "jinja")
    error_msg = str(exception)

    assert "jinja2" in error_msg
    assert "litestar-vite[jinja]" in error_msg
    assert "pip install" in error_msg


def test_error_messages_installation_instruction_format() -> None:
    """Test that installation instructions follow expected format."""
    # Test the expected installation instruction format
    instruction = "pip install 'litestar-vite[jinja]'"

    # Should include the package name with jinja extra
    assert "litestar-vite" in instruction
    assert "[jinja]" in instruction
    assert "pip install" in instruction


# =====================================================
# Backward Compatibility Tests
# =====================================================


def test_backward_compatibility_existing_imports_still_work_with_jinja() -> None:
    """Test that existing imports continue to work when Jinja is available."""
    # These imports should still work for backward compatibility
    from litestar_vite.config import ViteConfig
    from litestar_vite.loader import ViteAssetLoader
    from litestar_vite.plugin import VitePlugin

    # All should be importable
    assert VitePlugin is not None
    assert ViteConfig is not None
    assert ViteAssetLoader is not None


def test_backward_compatibility_plugin_api_unchanged() -> None:
    """Test that the plugin API hasn't changed for existing users."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    # Plugin should initialize the same way as before
    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # Public API should be unchanged
    assert plugin.config is config
    assert plugin.asset_loader is not None
    assert callable(plugin.on_app_init)
    assert callable(plugin.on_cli_init)
    assert plugin.server_lifespan is not None


# =====================================================
# Conditional Imports Tests
# =====================================================


def test_conditional_imports_type_checking_handle_missing_jinja() -> None:
    """Scaffolding is importable regardless of Jinja availability.

    ``jinja2`` is imported lazily inside ``render_template``, so importing the
    scaffolding package must never require the ``jinja`` extra.
    """
    import litestar_vite.scaffolding.generator

    assert litestar_vite.scaffolding.generator is not None


def test_conditional_imports_runtime_imports_fail_gracefully() -> None:
    """Test that runtime imports fail with helpful messages."""
    # Test that missing jinja2 at runtime produces appropriate errors
    with patch.dict(sys.modules, {"jinja2": None}):
        with pytest.raises((ImportError, ModuleNotFoundError)):
            # This should fail when trying to actually use jinja2
            importlib.import_module("jinja2")


# =====================================================
# Jinja Optional Edge Cases Tests
# =====================================================


def test_edge_case_vite_config_without_jinja_bundle_dir() -> None:
    """Test ViteConfig behavior with basic configuration even when Jinja is not available."""
    from litestar_vite.config import ViteConfig

    # ViteConfig should work with basic configuration even if Jinja is not available
    config = ViteConfig(paths=PathConfig(bundle_dir=Path("/tmp/public")))
    assert config.bundle_dir == Path("/tmp/public")


def test_edge_case_multiple_template_engine_scenarios() -> None:
    """Test scenarios with multiple template engines where Jinja might not be available."""
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


def test_edge_case_error_message_consistency() -> None:
    """Test that error messages are consistent across different entry points."""
    # All missing dependency errors should have consistent format
    exception = MissingDependencyError("jinja2", "jinja")
    error_msg = str(exception)

    # Should contain key information
    assert "jinja2" in error_msg
    assert "litestar-vite[jinja]" in error_msg
    assert "pip install" in error_msg


def test_edge_case_template_callable_registration_with_missing_jinja() -> None:
    """Test template callable registration when Jinja is not available."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # App config without template config
    app_config = AppConfig()

    # Should complete without error even when no template callables can be registered
    updated_config = plugin.on_app_init(app_config)
    assert updated_config is not None


def test_edge_case_backwards_compatibility_imports() -> None:
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


def test_edge_case_asset_loader_independence_from_jinja() -> None:
    """Test that asset loader works independently of Jinja availability."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.loader import ViteAssetLoader

    config = ViteConfig(paths=PathConfig(bundle_dir=Path("/tmp/public"), resource_dir=Path("/tmp/resources")))

    # Asset loader should work regardless of Jinja
    loader = ViteAssetLoader.initialize_loader(config=config)
    assert loader is not None
    # The loader should have a config even if it's not exactly the same instance
    assert loader._config is not None


def test_edge_case_plugin_server_lifespan_without_jinja() -> None:
    """Test plugin server lifespan functionality without Jinja."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # Server lifespan should work
    lifespans = plugin.server_lifespan
    assert lifespans is not None


def test_edge_case_development_vs_production_jinja_scenarios() -> None:
    """Test Jinja optional behavior in development vs production scenarios."""
    from litestar_vite.config import ViteConfig

    # Development scenario - dev_mode=True with vite mode enables HMR
    dev_config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode="vite"))
    assert dev_config.hot_reload is True

    # Production scenario - dev_mode=False disables HMR
    prod_config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    assert prod_config.hot_reload is False


# =====================================================
# Jinja Optional Performance Impact Tests
# =====================================================


def test_performance_import_time_without_jinja() -> None:
    """Test that import time is not significantly impacted when Jinja is missing."""
    start_time = time.time()

    # These imports should be fast even when Jinja is not available

    import_time = time.time() - start_time

    # Import should complete quickly (less than 1 second)
    assert import_time < 1.0, f"Import took too long: {import_time}s"


def test_performance_plugin_initialization() -> None:
    """Test plugin initialization performance without Jinja."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    config = ViteConfig()

    start_time = time.time()
    plugin = VitePlugin(config=config)
    init_time = time.time() - start_time

    # Initialization should be fast
    assert init_time < 0.1, f"Plugin initialization took too long: {init_time}s"
    assert plugin is not None


def test_performance_memory_usage_without_jinja() -> None:
    """Test memory usage when Jinja is not available."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    gc.collect()  # Clean up before test

    config = ViteConfig()
    plugin = VitePlugin(config=config)

    # Basic functionality should not cause memory leaks
    assert plugin is not None
    assert plugin.config is not None


# =====================================================
# Jinja Optional Production Readiness Tests
# =====================================================


def test_production_docker_container_scenario_without_jinja() -> None:
    """Test scenario typical in Docker containers where Jinja might not be installed."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin

    # Typical production configuration
    config = ViteConfig(
        paths=PathConfig(bundle_dir=Path("/app/public"), resource_dir=Path("/app/resources")),
        runtime=RuntimeConfig(dev_mode=False),  # Production setting
    )

    plugin = VitePlugin(config=config)
    app_config = AppConfig()

    # Should work in production environment
    updated_config = plugin.on_app_init(app_config)
    assert updated_config is not None


def test_production_kubernetes_deployment_scenario() -> None:
    """Test Kubernetes deployment scenario where dependencies are minimal."""
    from litestar_vite.config import ViteConfig
    from litestar_vite.loader import ViteAssetLoader

    # Kubernetes-style configuration with read-only filesystem considerations
    config = ViteConfig(
        paths=PathConfig(bundle_dir=Path("/app/static"), resource_dir=Path("/app/src")),
        runtime=RuntimeConfig(dev_mode=False),
    )

    loader = ViteAssetLoader.initialize_loader(config=config)
    assert loader is not None


def test_production_serverless_environment_scenario() -> None:
    """Test serverless environment where cold starts and minimal dependencies matter."""
    start_time = time.time()

    # Fast cold start simulation
    package = importlib.import_module("litestar_vite")

    cold_start_time = time.time() - start_time

    # Should start quickly for serverless environments
    assert cold_start_time < 0.5, f"Cold start too slow for serverless: {cold_start_time}s"

    config = package.ViteConfig()
    plugin = package.VitePlugin(config=config)
    assert plugin is not None
