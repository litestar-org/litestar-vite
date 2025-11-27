"""Tests for litestar_vite.commands module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.anyio


class TestInitVite:
    """Test init_vite function."""

    def test_init_vite_creates_project(self, tmp_path: Path) -> None:
        """Test that init_vite creates a project with the new scaffolding system."""
        from litestar_vite.commands import init_vite

        app = Mock()

        init_vite(
            app=app,
            root_path=tmp_path,
            resource_path=Path("resources"),
            asset_url="/static/",
            public_path=Path("public"),
            bundle_path=Path("dist"),
            enable_ssr=False,
            vite_port=5173,
            hot_file=Path("hot"),
            litestar_port=8000,
        )

        # Check that core files were created
        assert (tmp_path / "vite.config.ts").exists()
        assert (tmp_path / "package.json").exists()
        # React template creates main.tsx
        assert (tmp_path / "resources" / "main.tsx").exists()

    def test_init_vite_with_framework(self, tmp_path: Path) -> None:
        """Test init_vite with different framework templates."""
        from litestar_vite.commands import init_vite

        app = Mock()

        init_vite(
            app=app,
            root_path=tmp_path,
            resource_path=Path("resources"),
            asset_url="/static/",
            public_path=Path("public"),
            bundle_path=Path("dist"),
            enable_ssr=False,
            vite_port=5173,
            hot_file=Path("hot"),
            litestar_port=8000,
            framework="vue",
        )

        # Check that Vue-specific files were created
        assert (tmp_path / "vite.config.ts").exists()
        assert (tmp_path / "resources" / "main.ts").exists()
        assert (tmp_path / "resources" / "App.vue").exists()

    @patch("litestar_vite.commands.JINJA_INSTALLED", False)
    def test_init_vite_error_when_jinja_missing(self, tmp_path: Path) -> None:
        """Test init_vite raises appropriate error when Jinja is missing."""
        from litestar_vite.exceptions import MissingDependencyError

        app = Mock()

        with pytest.raises(MissingDependencyError) as exc_info:
            from litestar_vite.commands import init_vite

            init_vite(
                app=app,
                root_path=tmp_path,
                resource_path=Path("resources"),
                asset_url="/static/",
                public_path=Path("public"),
                bundle_path=Path("dist"),
                enable_ssr=False,
                vite_port=5173,
                hot_file=Path("hot"),
                litestar_port=8000,
            )

        assert "jinja" in str(exc_info.value).lower()


class TestScaffoldingModule:
    """Test the scaffolding module directly."""

    def test_get_available_templates(self) -> None:
        """Test that get_available_templates returns all templates."""
        from litestar_vite.scaffolding import get_available_templates

        templates = get_available_templates()
        assert len(templates) >= 8  # At least 8 framework templates

        # Check that expected frameworks are present
        template_names = [t.type.value for t in templates]
        assert "react" in template_names
        assert "vue" in template_names
        assert "svelte" in template_names

    def test_get_template_by_string(self) -> None:
        """Test getting a template by string name."""
        from litestar_vite.scaffolding.templates import get_template

        template = get_template("react")
        assert template is not None
        assert template.name == "React"

    def test_get_template_by_enum(self) -> None:
        """Test getting a template by enum."""
        from litestar_vite.scaffolding.templates import FrameworkType, get_template

        template = get_template(FrameworkType.VUE)
        assert template is not None
        assert template.name == "Vue 3"

    def test_get_template_invalid(self) -> None:
        """Test getting an invalid template returns None."""
        from litestar_vite.scaffolding.templates import get_template

        template = get_template("invalid-framework")
        assert template is None

    def test_template_context_to_dict(self) -> None:
        """Test TemplateContext.to_dict() method."""
        from litestar_vite.scaffolding import TemplateContext
        from litestar_vite.scaffolding.templates import get_template

        framework = get_template("react")
        assert framework is not None

        context = TemplateContext(
            project_name="test-project",
            framework=framework,
            use_typescript=True,
            vite_port=5173,
            litestar_port=8000,
        )

        context_dict = context.to_dict()
        assert context_dict["project_name"] == "test-project"
        assert context_dict["framework"] == "react"
        assert context_dict["use_typescript"] is True

    def test_generate_project(self, tmp_path: Path) -> None:
        """Test generate_project creates files correctly."""
        from litestar_vite.scaffolding import TemplateContext, generate_project
        from litestar_vite.scaffolding.templates import get_template

        framework = get_template("react")
        assert framework is not None

        context = TemplateContext(
            project_name="test-project",
            framework=framework,
            use_typescript=True,
            vite_port=5173,
            litestar_port=8000,
        )

        generated = generate_project(tmp_path, context)

        assert len(generated) > 0
        assert (tmp_path / "vite.config.ts").exists()

    def test_inertia_templates_exist(self) -> None:
        """Test that Inertia templates are available."""
        from litestar_vite.scaffolding.templates import FrameworkType, get_template

        react_inertia = get_template(FrameworkType.REACT_INERTIA)
        assert react_inertia is not None
        assert react_inertia.inertia_compatible is True

        vue_inertia = get_template(FrameworkType.VUE_INERTIA)
        assert vue_inertia is not None
        assert vue_inertia.inertia_compatible is True

        svelte_inertia = get_template(FrameworkType.SVELTE_INERTIA)
        assert svelte_inertia is not None
        assert svelte_inertia.inertia_compatible is True
