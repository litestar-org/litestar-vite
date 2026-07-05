"""Tests for litestar_vite.commands module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from litestar.serialization import decode_json

from litestar_vite.scaffolding.templates import CURRENT_NPM_VERSION_RANGES as V

pytestmark = pytest.mark.anyio


# =====================================================
# init_vite Function Tests
# =====================================================


def test_init_vite_creates_project(tmp_path: Path) -> None:
    """Test that init_vite creates a project with the new scaffolding system."""
    from litestar_vite.commands import init_vite

    init_vite(
        root_path=tmp_path,
        resource_path=Path("src"),
        asset_url="/static/",
        static_path=Path("public"),
        bundle_path=Path("dist"),
        enable_ssr=False,
        vite_port=5173,
        litestar_port=8000,
    )

    # Check that core files were created
    assert (tmp_path / "vite.config.ts").exists()
    assert (tmp_path / "package.json").exists()
    # React template creates main.tsx
    assert (tmp_path / "src" / "main.tsx").exists()


def test_init_vite_with_framework(tmp_path: Path) -> None:
    """Test init_vite with different framework templates."""
    from litestar_vite.commands import init_vite

    init_vite(
        root_path=tmp_path,
        resource_path=Path("src"),
        asset_url="/static/",
        static_path=Path("public"),
        bundle_path=Path("dist"),
        enable_ssr=False,
        vite_port=5173,
        litestar_port=8000,
        framework="vue",
    )

    # Check that Vue-specific files were created
    assert (tmp_path / "vite.config.ts").exists()
    assert (tmp_path / "src" / "main.ts").exists()
    assert (tmp_path / "src" / "App.vue").exists()


@patch("litestar_vite.commands.JINJA_INSTALLED", False)
def test_init_vite_error_when_jinja_missing(tmp_path: Path) -> None:
    """Test init_vite raises appropriate error when Jinja is missing."""
    from litestar_vite.exceptions import MissingDependencyError

    with pytest.raises(MissingDependencyError) as exc_info:
        from litestar_vite.commands import init_vite

        init_vite(
            root_path=tmp_path,
            resource_path=Path("resources"),
            asset_url="/static/",
            static_path=Path("public"),
            bundle_path=Path("dist"),
            enable_ssr=False,
            vite_port=5173,
            litestar_port=8000,
        )

    assert "jinja" in str(exc_info.value).lower()


# =====================================================
# Scaffolding Module Tests
# =====================================================


def test_scaffolding_get_available_templates() -> None:
    """Test that get_available_templates returns all templates."""
    from litestar_vite.scaffolding import get_available_templates

    templates = get_available_templates()
    assert len(templates) >= 8  # At least 8 framework templates

    # Check that expected frameworks are present
    template_names = [t.type.value for t in templates]
    assert "react" in template_names
    assert "vue" in template_names
    assert "svelte" in template_names
    assert "angular" in template_names
    assert "angular-cli" in template_names


def test_scaffolding_get_template_by_string() -> None:
    """Test getting a template by string name."""
    from litestar_vite.scaffolding.templates import get_template

    template = get_template("react")
    assert template is not None
    assert template.name == "React"


def test_scaffolding_get_template_by_enum() -> None:
    """Test getting a template by enum."""
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    template = get_template(FrameworkType.VUE)
    assert template is not None
    assert template.name == "Vue"


def test_scaffolding_get_template_invalid() -> None:
    """Test getting an invalid template returns None."""
    from litestar_vite.scaffolding.templates import get_template

    template = get_template("invalid-framework")
    assert template is None


def test_scaffolding_template_context_to_dict() -> None:
    """Test TemplateContext.to_dict() method."""
    from litestar_vite.scaffolding import TemplateContext
    from litestar_vite.scaffolding.templates import get_template

    framework = get_template("react")
    assert framework is not None

    context = TemplateContext(
        project_name="test-project", framework=framework, use_typescript=True, vite_port=5173, litestar_port=8000
    )

    context_dict = context.to_dict()
    assert context_dict["project_name"] == "test-project"
    assert context_dict["framework"] == "react"
    assert context_dict["use_typescript"] is True


def test_scaffolding_generate_project(tmp_path: Path) -> None:
    """Test generate_project creates files correctly."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import get_template

    framework = get_template("react")
    assert framework is not None

    context = TemplateContext(
        project_name="test-project", framework=framework, use_typescript=True, vite_port=5173, litestar_port=8000
    )

    generated = generate_project(tmp_path, context)

    assert len(generated) > 0
    assert (tmp_path / "vite.config.ts").exists()


def test_scaffolding_inertia_templates_exist() -> None:
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


def test_scaffolding_angular_templates_registered() -> None:
    """Test that Angular templates are properly registered."""
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    angular = get_template(FrameworkType.ANGULAR)
    cli = get_template(FrameworkType.ANGULAR_CLI)

    assert angular is not None
    assert angular.uses_vite is True
    assert angular.resource_dir == "src"

    assert cli is not None
    assert cli.uses_vite is False
    assert cli.resource_dir == "src"


def test_scaffolding_generate_project_angular_overrides_base_files(tmp_path: Path) -> None:
    """Test that Angular template overrides base files correctly."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.ANGULAR)
    assert framework is not None

    context = TemplateContext(
        project_name="ng-lite",
        framework=framework,
        use_typescript=True,
        vite_port=5173,
        litestar_port=8000,
        resource_dir=framework.resource_dir,
    )

    generated = generate_project(tmp_path, context)

    assert (tmp_path / "vite.config.ts").exists()
    assert (tmp_path / "tsconfig.json").exists()
    assert (tmp_path / "src" / "app" / "app.component.ts").exists()
    # Ensure Angular-specific tsconfig (Bundler resolution) was written, not base
    tsconfig = (tmp_path / "tsconfig.json").read_text()
    assert "moduleResolution" in tsconfig
    assert any(p.name == "tsconfig.json" for p in generated)


def test_scaffolding_generate_project_angular_cli_skips_vite_base(tmp_path: Path) -> None:
    """Test that Angular CLI template skips Vite base files."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.ANGULAR_CLI)
    assert framework is not None

    context = TemplateContext(
        project_name="ng-cli-lite",
        framework=framework,
        use_typescript=True,
        resource_dir=framework.resource_dir,
        bundle_dir="dist",
    )

    generate_project(tmp_path, context)

    package_json = decode_json((tmp_path / "package.json").read_text())
    dev_deps = package_json.get("devDependencies", {})
    angular_json = (tmp_path / "angular.json").read_text()
    styles = (tmp_path / "src" / "styles.css").read_text()

    assert "litestar-vite-plugin" not in dev_deps
    assert (tmp_path / "angular.json").exists()
    assert dev_deps["@angular/build"] == V["@angular/build"]
    assert dev_deps["@angular/cli"] == V["@angular/cli"]
    assert dev_deps["@angular/compiler-cli"] == V["@angular/compiler-cli"]
    assert dev_deps["@tailwindcss/postcss"] == V["@tailwindcss/postcss"]
    assert dev_deps["postcss"] == V["postcss"]
    assert dev_deps["tailwindcss"] == V["tailwindcss"]
    assert "autoprefixer" not in dev_deps
    assert "@types/jasmine" not in dev_deps
    assert "@angular/build:application" in angular_json
    assert "@angular/build:dev-server" in angular_json
    assert "@angular-devkit/build-angular" not in angular_json
    assert "src/generated" not in angular_json
    assert "@config" not in styles
    assert (tmp_path / ".postcssrc.json").exists()
    assert not (tmp_path / "tailwind.config.js").exists()
    assert not (tmp_path / "tsconfig.spec.json").exists()


def test_scaffolding_generate_project_htmx_uses_current_extension_shell(tmp_path: Path) -> None:
    """Test that HTMX scaffolding uses pinned versions and the Litestar extension shell."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.HTMX)
    assert framework is not None

    context = TemplateContext(
        project_name="htmx-lite",
        framework=framework,
        use_typescript=False,
        use_tailwind=True,
        resource_dir=framework.resource_dir,
    )

    generate_project(tmp_path, context)

    package_json = decode_json((tmp_path / "package.json").read_text())
    base_template = (tmp_path / "templates" / "base.html.j2").read_text()

    assert package_json["dependencies"]["htmx.org"] == V["htmx.org"]
    assert package_json["devDependencies"]["@tailwindcss/vite"] == V["@tailwindcss/vite"]
    assert package_json["devDependencies"]["@tailwindcss/postcss"] == V["@tailwindcss/postcss"]
    assert package_json["devDependencies"]["postcss"] == V["postcss"]
    assert package_json["devDependencies"]["tailwindcss"] == V["tailwindcss"]
    assert package_json["devDependencies"]["typescript"] == V["typescript"]
    assert package_json["devDependencies"]["vite"] == V["vite"]
    assert 'meta name="csrf-token"' in base_template
    assert 'body hx-ext="litestar"' in base_template
    assert (tmp_path / "resources" / "tailwind.css").exists()
    assert '"resources/tailwind.css"' in (tmp_path / "vite.config.ts").read_text()


def test_scaffolding_react_tanstack_raw_package_template_does_not_duplicate_default_api_deps() -> None:
    """Ensure TanStack package deps are unique before generated files are written."""
    from litestar_vite.scaffolding import TemplateContext
    from litestar_vite.scaffolding.generator import render_template
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    root = Path(__file__).resolve().parents[4]
    framework = get_template(FrameworkType.REACT_TANSTACK)
    assert framework is not None

    context = TemplateContext(
        project_name="tanstack-lite", framework=framework, use_tailwind=True, generate_zod=True, generate_client=True
    )

    package_text = render_template(
        root / "src" / "py" / "litestar_vite" / "templates" / "base" / "package.json.j2", context.to_dict()
    )

    assert package_text.count('"zod"') == 1
    assert package_text.count('"@hey-api/openapi-ts"') == 1


def test_scaffolding_generate_project_react_tanstack_has_unique_default_api_deps(tmp_path: Path) -> None:
    """Ensure generated TanStack package.json parses and keeps default API deps once."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.REACT_TANSTACK)
    assert framework is not None

    context = TemplateContext(
        project_name="tanstack-lite", framework=framework, use_tailwind=True, generate_zod=True, generate_client=True
    )

    generate_project(tmp_path, context)

    package_text = (tmp_path / "package.json").read_text()
    package_json = decode_json(package_text)

    assert package_text.count('"zod"') == 1
    assert package_text.count('"@hey-api/openapi-ts"') == 1
    assert package_json["dependencies"]["zod"] == V["zod"]
    assert package_json["devDependencies"]["@hey-api/openapi-ts"] == V["@hey-api/openapi-ts"]

    openapi_config = (tmp_path / "openapi-ts.config.ts").read_text()
    vite_config = (tmp_path / "vite.config.ts").read_text()
    assert "client:" not in openapi_config
    assert '"@hey-api/client-fetch"' in openapi_config
    assert "tanstackRouter" in vite_config
    assert "TanStackRouterVite" not in vite_config


def test_scaffolding_generate_project_react_tanstack_keeps_default_api_deps_when_flags_disabled(tmp_path: Path) -> None:
    """Ensure TanStack keeps its API deps under the template-default contract."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.REACT_TANSTACK)
    assert framework is not None

    context = TemplateContext(
        project_name="tanstack-lite", framework=framework, generate_zod=False, generate_client=False
    )

    generate_project(tmp_path, context)

    package_text = (tmp_path / "package.json").read_text()
    package_json = decode_json(package_text)

    assert package_text.count('"zod"') == 1
    assert package_text.count('"@hey-api/openapi-ts"') == 1
    assert package_json["dependencies"]["zod"] == V["zod"]
    assert package_json["devDependencies"]["@hey-api/openapi-ts"] == V["@hey-api/openapi-ts"]


def test_scaffolding_generate_project_react_inertia_jinja_has_unique_vite_dev_dep(tmp_path: Path) -> None:
    """Ensure base-rendered Inertia Jinja package.json keeps Vite once."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.REACT_INERTIA_JINJA)
    assert framework is not None

    context = TemplateContext(project_name="inertia-lite", framework=framework)

    generate_project(tmp_path, context)

    package_text = (tmp_path / "package.json").read_text()
    package_json = decode_json(package_text)

    assert package_text.count('    "vite":') == 1
    assert package_json["devDependencies"]["vite"] == V["vite"]


def test_scaffolding_dirless_variants_use_family_templates(tmp_path: Path) -> None:
    """Registered variants without a directory should still render usable family templates."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    variants = [
        (FrameworkType.REACT_INERTIA_JINJA, "resources/main.tsx"),
        (FrameworkType.VUE_INERTIA_SSR, "resources/main.ts"),
        (FrameworkType.VUE_INERTIA_JINJA, "resources/main.ts"),
        (FrameworkType.VUE_INERTIA_JINJA_SSR, "resources/main.ts"),
        (FrameworkType.SVELTE_INERTIA_JINJA, "resources/main.ts"),
        (FrameworkType.JINJA_HTMX, "resources/main.js"),
        (FrameworkType.HTMX_NO_JINJA, "resources/main.js"),
    ]

    for framework_type, expected_file in variants:
        target = tmp_path / framework_type.value
        framework = get_template(framework_type)
        assert framework is not None
        generate_project(
            target,
            TemplateContext(
                project_name=framework_type.value,
                framework=framework,
                resource_dir=framework.resource_dir,
                enable_ssr=framework.has_ssr,
                enable_inertia=framework.inertia_compatible,
            ),
        )

        assert (target / expected_file).exists()
        assert (target / "package.json").exists()


def test_scaffolding_render_failure_leaves_no_partial_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed render should not write earlier files from the same scaffold."""
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding import generator as generator_module
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    framework = get_template(FrameworkType.REACT)
    assert framework is not None

    real_render = generator_module.render_template

    def fail_on_vite_config(template_path: Path, context: dict[str, object]) -> str:
        if template_path.name == "vite.config.ts.j2":
            raise RuntimeError("boom")
        return real_render(template_path, context)

    monkeypatch.setattr(generator_module, "render_template", fail_on_vite_config)

    with pytest.raises(RuntimeError, match="boom"):
        generate_project(tmp_path, TemplateContext(project_name="broken", framework=framework))

    assert not any(tmp_path.iterdir())


def test_scaffolding_generated_package_manifests_pin_dependency_versions(tmp_path: Path) -> None:
    """Ensure scaffold and example package manifests do not emit floating `latest` versions."""
    root = Path(__file__).resolve().parents[4]

    for package_template in (root / "src" / "py" / "litestar_vite" / "templates").rglob("package.json.j2"):
        assert '"latest"' not in package_template.read_text(), (
            f"{package_template}: package template should pin versions"
        )

    for example_package in (root / "examples").rglob("package.json"):
        if "node_modules" in example_package.parts:
            continue
        assert '"latest"' not in example_package.read_text(), f"{example_package}: example package should pin versions"
