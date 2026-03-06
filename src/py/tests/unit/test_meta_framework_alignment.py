from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_ROOT = ROOT / "examples"
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"


def test_astro_example_uses_current_manifest_and_tsconfig() -> None:
    package_text = (EXAMPLES_ROOT / "astro" / "package.json").read_text()
    tsconfig_text = (EXAMPLES_ROOT / "astro" / "tsconfig.json").read_text()
    layout_text = (EXAMPLES_ROOT / "astro" / "src" / "layouts" / "Layout.astro").read_text()

    assert '"astro": "5.18.0"' in package_text
    assert '"@hey-api/openapi-ts": "0.94.0"' in package_text
    assert '"@tailwindcss/vite": "4.2.1"' in package_text
    assert '"tailwindcss": "4.2.1"' in package_text
    assert '"vite": "7.3.1"' in package_text
    assert '"zod": "4.3.6"' in package_text
    assert '"check": "astro check"' in package_text
    assert '"typecheck": "astro check"' in package_text
    assert '"latest"' not in package_text

    assert '"extends": "astro/tsconfigs/strict"' in tsconfig_text
    assert '".astro/types.d.ts"' in tsconfig_text
    assert '"**/*"' in tsconfig_text
    assert '"dist"' in tsconfig_text

    assert 'import "../styles/global.css"' in layout_text
    assert "favicon.svg" not in layout_text


def test_nuxt_example_uses_current_manifest_and_app_directory() -> None:
    package_text = (EXAMPLES_ROOT / "nuxt" / "package.json").read_text()
    tsconfig_text = (EXAMPLES_ROOT / "nuxt" / "tsconfig.json").read_text()
    config_text = (EXAMPLES_ROOT / "nuxt" / "nuxt.config.ts").read_text()
    app_text = (EXAMPLES_ROOT / "nuxt" / "app" / "app.vue").read_text()
    composable_text = (EXAMPLES_ROOT / "nuxt" / "app" / "composables" / "useApi.ts").read_text()
    css_text = (EXAMPLES_ROOT / "nuxt" / "app" / "assets" / "css" / "app.css").read_text()

    assert '"nuxt": "4.3.1"' in package_text
    assert '"vue": "3.5.29"' in package_text
    assert '"@hey-api/openapi-ts": "0.94.0"' in package_text
    assert '"@tailwindcss/vite": "4.2.1"' in package_text
    assert '"tailwindcss": "4.2.1"' in package_text
    assert '"typescript": "5.9.3"' in package_text
    assert '"vite": "7.3.1"' in package_text
    assert '"vue-tsc": "3.2.5"' in package_text
    assert '"zod": "4.3.6"' in package_text
    assert '"dev": "nuxt dev"' in package_text
    assert '"build": "nuxt build"' in package_text
    assert '"preview": "nuxt preview"' in package_text
    assert '"postinstall": "nuxt prepare"' in package_text
    assert '"typecheck": "vue-tsc -b --noEmit"' in package_text
    assert '"latest"' not in package_text

    assert '"references": [' in tsconfig_text
    assert '"path": "./.nuxt/tsconfig.app.json"' in tsconfig_text
    assert '"path": "./.nuxt/tsconfig.server.json"' in tsconfig_text
    assert '"path": "./.nuxt/tsconfig.shared.json"' in tsconfig_text

    assert 'compatibilityDate: "2026-03-06"' in config_text
    assert 'css: ["~/assets/css/app.css"]' in config_text

    assert "<style" not in app_text
    assert '@import "tailwindcss";' in css_text
    assert "import.meta.client" in composable_text
    assert "config.public.apiProxy" in composable_text
    assert "config.public.apiPrefix" in composable_text


def test_meta_framework_templates_override_stale_base_files() -> None:
    astro_package = TEMPLATE_ROOT / "astro" / "package.json.j2"
    astro_tsconfig = TEMPLATE_ROOT / "astro" / "tsconfig.json.j2"
    astro_layout = (TEMPLATE_ROOT / "astro" / "src" / "layouts" / "Layout.astro.j2").read_text()

    nuxt_package = TEMPLATE_ROOT / "nuxt" / "package.json.j2"
    nuxt_tsconfig = TEMPLATE_ROOT / "nuxt" / "tsconfig.json.j2"
    nuxt_config = (TEMPLATE_ROOT / "nuxt" / "nuxt.config.ts.j2").read_text()
    nuxt_app = TEMPLATE_ROOT / "nuxt" / "app" / "app.vue.j2"
    nuxt_page = TEMPLATE_ROOT / "nuxt" / "app" / "pages" / "index.vue.j2"
    nuxt_composable = (TEMPLATE_ROOT / "nuxt" / "app" / "composables" / "useApi.ts.j2").read_text()
    nuxt_css = (TEMPLATE_ROOT / "nuxt" / "app" / "assets" / "css" / "app.css.j2").read_text()

    assert astro_package.exists()
    assert astro_tsconfig.exists()
    assert 'import "../styles/global.css";' in astro_layout
    assert "favicon.svg" not in astro_layout

    assert nuxt_package.exists()
    assert nuxt_tsconfig.exists()
    assert 'compatibilityDate: "2026-03-06"' in nuxt_config
    assert 'css: ["~/assets/css/app.css"]' in nuxt_config
    assert nuxt_app.exists()
    assert nuxt_page.exists()
    assert "config.public.apiProxy" in nuxt_composable
    assert "config.public.apiPrefix" in nuxt_composable
    assert '@import "tailwindcss";' in nuxt_css

    assert not (TEMPLATE_ROOT / "nuxt" / "app.vue.j2").exists()
    assert not (TEMPLATE_ROOT / "nuxt" / "pages" / "index.vue.j2").exists()
    assert not (TEMPLATE_ROOT / "nuxt" / "composables" / "useApi.ts.j2").exists()
