from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"
EXAMPLES_ROOT = ROOT / "examples"


def test_vue_examples_pin_current_stable_versions_and_use_vue_tsc_builds() -> None:
    vue = (EXAMPLES_ROOT / "vue" / "package.json").read_text()
    vue_inertia = (EXAMPLES_ROOT / "vue-inertia" / "package.json").read_text()
    vue_jinja = (EXAMPLES_ROOT / "vue-inertia-jinja" / "package.json").read_text()

    for text in (vue, vue_inertia, vue_jinja):
        assert '"build": "vue-tsc -b && vite build"' in text
        assert '"vue": "3.5.29"' in text
        assert '"@vitejs/plugin-vue": "6.0.4"' in text
        assert '"@vue/tsconfig": "0.9.0"' in text
        assert '"vue-tsc": "3.2.5"' in text
        assert '"typescript": "5.9.3"' in text
        assert '"vite": "7.3.1"' in text
        assert '"@tailwindcss/vite": "4.2.1"' in text
        assert '"tailwindcss": "4.2.1"' in text
        assert '"@hey-api/openapi-ts": "0.94.0"' in text
        assert '"@types/node": "25.3.5"' in text
        assert '"axios": "1.13.6"' in text
        assert '"latest"' not in text

    for text in (vue_inertia, vue_jinja):
        assert '"@inertiajs/vue3": "2.3.17"' in text
        assert '"zod": "4.3.6"' in text


def test_vue_examples_use_split_tsconfig_structure() -> None:
    for example_dir in ("vue", "vue-inertia", "vue-inertia-jinja"):
        tsconfig = (EXAMPLES_ROOT / example_dir / "tsconfig.json").read_text()
        tsconfig_app = (EXAMPLES_ROOT / example_dir / "tsconfig.app.json").read_text()
        tsconfig_node = (EXAMPLES_ROOT / example_dir / "tsconfig.node.json").read_text()

        assert '"references"' in tsconfig
        assert '"./tsconfig.app.json"' in tsconfig
        assert '"./tsconfig.node.json"' in tsconfig
        assert '"extends": "@vue/tsconfig/tsconfig.dom.json"' in tsconfig_app
        assert '"tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo"' in tsconfig_app
        assert '"types": ["vite/client"]' in tsconfig_app
        assert '"erasableSyntaxOnly": true' in tsconfig_app
        assert '"tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo"' in tsconfig_node
        assert '"types": ["node"]' in tsconfig_node
        assert '"verbatimModuleSyntax": true' in tsconfig_node


def test_vue_templates_match_stable_bootstrap_and_manifest_structure() -> None:
    vue_package = (TEMPLATE_ROOT / "vue" / "package.json.j2").read_text()
    vue_inertia_package = (TEMPLATE_ROOT / "vue-inertia" / "package.json.j2").read_text()
    vue_inertia_index = (TEMPLATE_ROOT / "vue-inertia" / "index.html.j2").read_text()
    vue_inertia_main = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "main.ts.j2").read_text()
    vue_inertia_ssr = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "ssr.ts.j2").read_text()

    assert '"build": "vue-tsc -b && vite build"' in vue_package
    assert '"vue": "3.5.29"' in vue_package
    assert '"@vue/tsconfig": "0.9.0"' in vue_package
    assert '"vue-tsc": "3.2.5"' in vue_package
    assert '"vite": "7.3.1"' in vue_package

    assert '"build": "vue-tsc -b && vite build && vite build --ssr {{ resource_dir }}/ssr.ts"' in vue_inertia_package
    assert '"@inertiajs/vue3": "2.3.17"' in vue_inertia_package
    assert '"@vue/server-renderer": "3.5.29"' in vue_inertia_package
    assert '"@hey-api/openapi-ts": "0.94.0"' in vue_inertia_package
    assert '"@types/node": "25.3.5"' in vue_inertia_package
    assert '"latest"' not in vue_inertia_package

    assert '<div id="app"></div>' in vue_inertia_index
    assert '<script type="module" src="/{{ resource_dir }}/main.ts"></script>' in vue_inertia_index
    assert "\n  defaults:" not in vue_inertia_main
    assert "useScriptElementForInitialPage: true" in vue_inertia_main
    assert "If you enable use_script_element=True" in vue_inertia_main
    assert "\n      defaults:" not in vue_inertia_ssr
    assert "defaults.future.useScriptElementForInitialPage" in vue_inertia_ssr
    assert "If you enable use_script_element=True" in vue_inertia_ssr


def test_vue_templates_use_split_tsconfig_structure() -> None:
    for template_dir in ("vue", "vue-inertia"):
        tsconfig = (TEMPLATE_ROOT / template_dir / "tsconfig.json.j2").read_text()
        tsconfig_app = (TEMPLATE_ROOT / template_dir / "tsconfig.app.json.j2").read_text()
        tsconfig_node = (TEMPLATE_ROOT / template_dir / "tsconfig.node.json.j2").read_text()

        assert '"references"' in tsconfig
        assert '"./tsconfig.app.json"' in tsconfig
        assert '"./tsconfig.node.json"' in tsconfig
        assert '"extends": "@vue/tsconfig/tsconfig.dom.json"' in tsconfig_app
        assert '"types": ["vite/client"]' in tsconfig_app
        assert '"{{ resource_dir }}/**/*.vue"' in tsconfig_app
        assert '"types": ["node"]' in tsconfig_node
        assert '"verbatimModuleSyntax": true' in tsconfig_node


def test_vue_examples_use_committed_route_snapshots() -> None:
    vue_app = (EXAMPLES_ROOT / "vue" / "src" / "App.vue").read_text()
    vue_routes = (EXAMPLES_ROOT / "vue" / "src" / "routes.ts").read_text()
    vue_inertia_home = (EXAMPLES_ROOT / "vue-inertia" / "resources" / "pages" / "Home.vue").read_text()
    vue_inertia_routes = (EXAMPLES_ROOT / "vue-inertia" / "resources" / "routes.ts").read_text()
    vue_jinja_home = (EXAMPLES_ROOT / "vue-inertia-jinja" / "resources" / "pages" / "Home.vue").read_text()
    vue_jinja_routes = (EXAMPLES_ROOT / "vue-inertia-jinja" / "resources" / "routes.ts").read_text()

    assert "@/routes" in vue_app
    assert "@/routes" in vue_inertia_home
    assert "@/routes" in vue_jinja_home
    assert "export const routeDefinitions = {" in vue_routes
    assert "export const routeDefinitions = {" in vue_inertia_routes
    assert "export const routeDefinitions = {" in vue_jinja_routes
