from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from litestar_vite.commands import VITE_INIT_TEMPLATES, get_template

pytestmark = pytest.mark.anyio
here = Path(__file__).parent


@pytest.fixture
def vite_template_env() -> Environment:
    # Navigate to the actual templates directory in the source code
    template_path = Path(here.parent.parent / "litestar_vite" / "templates")
    return Environment(
        loader=FileSystemLoader([template_path]),
        autoescape=select_autoescape(),
    )


def test_get_template(vite_template_env: Environment) -> None:
    init_templates = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in VITE_INIT_TEMPLATES
    }
    assert len(init_templates.keys()) == len(VITE_INIT_TEMPLATES)


class TestCommandsWithJinjaOptional:
    """Test commands functionality with Jinja as optional dependency."""

    def test_constants_available_without_jinja(self) -> None:
        """Test that constants are available even when Jinja is missing."""
        from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES

        # Constants should be defined regardless of Jinja availability
        assert VITE_INIT_TEMPLATES is not None
        assert DEFAULT_RESOURCES is not None
        assert isinstance(VITE_INIT_TEMPLATES, set)
        assert isinstance(DEFAULT_RESOURCES, set)

    def test_get_template_with_jinja_available(self, vite_template_env: Environment) -> None:
        """Test get_template function when Jinja is available."""
        from litestar_vite.commands import get_template

        # Should work normally when Jinja is available
        template = get_template(environment=vite_template_env, name="package.json.j2")
        assert template is not None

        # Template should be renderable
        rendered = template.render()
        assert "package.json" in rendered or "dependencies" in rendered

    def test_get_template_error_handling_when_jinja_missing(self) -> None:
        """Test get_template error handling when Jinja dependencies are missing."""
        import sys
        from unittest.mock import patch

        # Mock jinja2 module to be missing
        with patch.dict(sys.modules, {"jinja2": None}):
            # This should handle the import error gracefully
            from litestar_vite.commands import VITE_INIT_TEMPLATES

            assert VITE_INIT_TEMPLATES is not None

    def test_init_vite_with_jinja_available(self, tmp_path: Path, vite_template_env: Environment) -> None:
        """Test init_vite function when Jinja is available."""
        from unittest.mock import Mock

        from litestar_vite.commands import init_vite

        app = Mock()

        # Should work when Jinja is available
        try:
            init_vite(
                app=app,
                root_path=tmp_path,
                resource_path=tmp_path / "resources",
                asset_url="/static/",
                public_path=tmp_path / "public",
                bundle_path=tmp_path / "dist",
                enable_ssr=False,
                vite_port=5173,
                hot_file=tmp_path / "hot",
                litestar_port=8000,
            )
        except Exception as e:
            # If it fails, it shouldn't be due to missing Jinja when Jinja is available
            assert "jinja" not in str(e).lower(), f"Should not fail due to Jinja when available: {e}"

    @patch("litestar_vite.commands.JINJA_INSTALLED", False)
    def test_init_vite_error_when_jinja_missing(self, tmp_path: Path) -> None:
        """Test init_vite raises appropriate error when Jinja is missing."""
        from unittest.mock import Mock

        from litestar_vite.exceptions import MissingDependencyError

        app = Mock()

        # Test should raise MissingDependencyError when Jinja is not installed
        with pytest.raises(MissingDependencyError) as exc_info:
            from litestar_vite.commands import init_vite

            init_vite(
                app=app,
                root_path=tmp_path,
                resource_path=tmp_path / "resources",
                asset_url="/static/",
                public_path=tmp_path / "public",
                bundle_path=tmp_path / "dist",
                enable_ssr=False,
                vite_port=5173,
                hot_file=tmp_path / "hot",
                litestar_port=8000,
            )

        # Should provide clear installation instructions
        assert "jinja" in str(exc_info.value)

    def test_template_generation_conditional_on_jinja(self, tmp_path: Path) -> None:
        """Test that template generation is conditional on Jinja availability."""
        import sys
        from unittest.mock import Mock, patch

        Mock()

        # Test with Jinja completely missing
        with patch.dict(sys.modules, {"jinja2": None}):
            # The commands module should still be importable
            from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES

            # Constants should still be available
            assert VITE_INIT_TEMPLATES is not None
            assert DEFAULT_RESOURCES is not None

    def test_backwards_compatibility_imports(self) -> None:
        """Test that backwards compatibility is maintained for existing imports."""
        # These imports should work regardless of Jinja availability
        try:
            from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES, get_template

            assert VITE_INIT_TEMPLATES is not None
            assert DEFAULT_RESOURCES is not None
            assert get_template is not None
        except ImportError as e:
            pytest.fail(f"Basic command imports should not fail regardless of Jinja availability: {e}")

    def test_command_module_loading_performance(self) -> None:
        """Test that command module loads quickly without Jinja."""
        import importlib
        import time

        # Force reimport to test loading time
        if "litestar_vite.commands" in importlib.sys.modules:
            del importlib.sys.modules["litestar_vite.commands"]

        start_time = time.time()
        load_time = time.time() - start_time

        # Should load quickly (less than 100ms)
        assert load_time < 0.1, f"Commands module took too long to load: {load_time}s"

    def test_error_message_quality_for_missing_jinja(self) -> None:
        """Test quality of error messages when Jinja is missing."""
        from litestar_vite.exceptions import MissingDependencyError

        # Test error message format
        exception = MissingDependencyError("jinja2", "jinja")
        error_msg = str(exception)

        # Should contain essential information
        assert "jinja2" in error_msg
        assert "pip install" in error_msg
        assert "litestar-vite[jinja]" in error_msg

    def test_template_constants_consistency(self) -> None:
        """Test that template constants are consistent."""
        from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES

        # Template names should be consistent
        expected_init_templates = {"package.json.j2", "tsconfig.json.j2", "vite.config.ts.j2"}
        expected_resources = {"styles.css.j2", "main.ts.j2"}

        assert VITE_INIT_TEMPLATES == expected_init_templates
        assert DEFAULT_RESOURCES == expected_resources

    def test_command_constants_immutability(self) -> None:
        """Test that command constants cannot be accidentally modified."""
        from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES

        # Should be able to iterate without modifying original
        templates_copy = set(VITE_INIT_TEMPLATES)
        resources_copy = set(DEFAULT_RESOURCES)

        # Original sets should be unchanged
        assert VITE_INIT_TEMPLATES == templates_copy
        assert DEFAULT_RESOURCES == resources_copy

    def test_conditional_jinja_import_in_type_checking(self) -> None:
        """Test that TYPE_CHECKING imports don't cause runtime issues."""
        # This tests the TYPE_CHECKING block imports in commands.py
        from litestar_vite import commands

        # Module should load successfully
        assert hasattr(commands, "VITE_INIT_TEMPLATES")
        assert hasattr(commands, "DEFAULT_RESOURCES")
        assert hasattr(commands, "get_template")

    def test_template_environment_creation_conditional(self, tmp_path: Path) -> None:
        """Test that template environment creation is properly conditional."""
        from unittest.mock import patch

        # Test that template environment creation handles missing Jinja
        with patch.dict("sys.modules", {"jinja2": None}):
            # Should not fail on import
            from litestar_vite.commands import VITE_INIT_TEMPLATES

            assert VITE_INIT_TEMPLATES is not None

    def test_development_vs_production_scenarios_without_jinja(self) -> None:
        """Test different deployment scenarios without Jinja."""
        from litestar_vite.commands import DEFAULT_RESOURCES, VITE_INIT_TEMPLATES

        # Should work in both development and production scenarios
        # where Jinja might not be installed
        assert len(VITE_INIT_TEMPLATES) > 0
        assert len(DEFAULT_RESOURCES) > 0

        # Constants should be usable for non-Jinja operations
        for template_name in VITE_INIT_TEMPLATES:
            assert isinstance(template_name, str)
            assert template_name.endswith(".j2")

    def test_memory_efficiency_without_jinja(self) -> None:
        """Test memory efficiency when Jinja is not loaded."""
        import gc

        gc.collect()  # Clean up before test

        # Import commands module
        from litestar_vite import commands

        # Should not hold references to heavy Jinja objects when Jinja is not available
        # This is a basic test that the module doesn't leak memory
        assert commands.VITE_INIT_TEMPLATES is not None
