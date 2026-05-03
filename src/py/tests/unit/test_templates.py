from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"
EXAMPLES_ROOT = ROOT / "examples"


def _example_dir_names() -> set[str]:
    return {child.name for child in EXAMPLES_ROOT.iterdir() if child.is_dir() and (child / "app.py").exists()}


def test_framework_type_enum_includes_all_examples() -> None:
    """Every example/ subdirectory must have a matching FrameworkType enum value.

    Examples without enum entries are invisible to scaffolding lookups and risk
    drifting out of e2e parametrization (which discovers by directory name).
    """
    from litestar_vite.scaffolding.templates import FrameworkType

    enum_values = {ft.value for ft in FrameworkType}
    missing_in_enum = _example_dir_names() - enum_values
    assert not missing_in_enum, f"Examples without FrameworkType entries: {missing_in_enum}"


def test_framework_templates_covers_all_enum_values() -> None:
    """Every FrameworkType must have a matching FRAMEWORK_TEMPLATES entry."""
    from litestar_vite.scaffolding.templates import FRAMEWORK_TEMPLATES, FrameworkType

    enum_values = set(FrameworkType)
    template_keys = set(FRAMEWORK_TEMPLATES.keys())
    missing = enum_values - template_keys
    extra = template_keys - enum_values
    assert not missing, f"FrameworkType values without FRAMEWORK_TEMPLATES entries: {missing}"
    assert not extra, f"FRAMEWORK_TEMPLATES entries without FrameworkType: {extra}"


def test_c6_required_examples_exist() -> None:
    """C6 adds 4 examples for previously uncovered Mode x Framework x Inertia x Jinja cells, plus 2 SSR variants."""
    expected = {
        "react-router",
        "svelte-inertia",
        "svelte-inertia-jinja",
        "htmx-no-jinja",
        "vue-inertia-ssr",
        "vue-inertia-jinja-ssr",
    }
    missing = expected - _example_dir_names()
    assert not missing, f"C6 examples missing from examples/: {missing}"


def test_inertia_ssr_examples_have_runnable_node_render_entries() -> None:
    """vue-inertia-ssr and vue-inertia-jinja-ssr ship runnable Node /render servers.

    Locks the C6 SSR contract: each SSR example must have a real ``resources/ssr.ts``
    that runs ``createServer(...)`` from ``@inertiajs/vue3/server``, plus a
    ``start:ssr`` script in ``package.json`` and ``InertiaConfig(ssr=...)`` in app.py.
    Without these the Inertia SSR endpoint cannot be exercised end-to-end.
    """
    for name in ("vue-inertia-ssr", "vue-inertia-jinja-ssr"):
        example = EXAMPLES_ROOT / name
        ssr_entry = example / "resources" / "ssr.ts"
        package_json = (example / "package.json").read_text()
        app_py = (example / "app.py").read_text()

        assert ssr_entry.exists(), f"{name}: missing resources/ssr.ts SSR runner entry"
        ssr_text = ssr_entry.read_text()
        assert "@inertiajs/vue3/server" in ssr_text, f"{name}: ssr.ts must import @inertiajs/vue3/server"
        assert "createServer" in ssr_text, f"{name}: ssr.ts must call createServer"
        assert "13714" in ssr_text or "INERTIA_SSR_PORT" in ssr_text, f"{name}: ssr.ts must bind 13714 (or use INERTIA_SSR_PORT env)"

        assert "start:ssr" in package_json, f"{name}: package.json must define a start:ssr script"
        assert "build:ssr" in package_json, f"{name}: package.json must define a build:ssr script"
        assert "@vue/server-renderer" in package_json, f"{name}: package.json must include @vue/server-renderer"

        assert "InertiaConfig" in app_py and "ssr=" in app_py, (
            f"{name}: app.py must construct InertiaConfig(ssr=...) so the handler frame POSTs to /render"
        )

    # The Jinja-shell SSR example must wire a Jinja TemplateConfig (template mode).
    jinja_app_py = (EXAMPLES_ROOT / "vue-inertia-jinja-ssr" / "app.py").read_text()
    assert "TemplateConfig" in jinja_app_py and "JinjaTemplateEngine" in jinja_app_py, (
        "vue-inertia-jinja-ssr: must wire JinjaTemplateEngine via TemplateConfig (template mode contract)"
    )
    assert (EXAMPLES_ROOT / "vue-inertia-jinja-ssr" / "templates" / "index.html").exists(), (
        "vue-inertia-jinja-ssr: must ship templates/index.html Jinja shell"
    )


def test_vue_inertia_ssr_example_invokes_ssr_endpoint() -> None:
    """The vue-inertia-ssr example POSTs to the Inertia SSR endpoint when serving an Inertia handler.

    Imports the example app and patches the SSR client so we never actually open a socket;
    asserts the Inertia handler frame issues the POST and the rendered HTML is injected back
    into the SPA shell. This locks the example's wiring without requiring a real Node process.
    """
    import importlib.util
    import sys
    from unittest.mock import AsyncMock, patch

    from litestar.testing import TestClient

    from litestar_vite.inertia.response import _InertiaSSRResult

    example_dir = EXAMPLES_ROOT / "vue-inertia-ssr"
    spec = importlib.util.spec_from_file_location("_vue_inertia_ssr_example", example_dir / "app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_vue_inertia_ssr_example"] = module
    try:
        spec.loader.exec_module(module)
        with patch(
            "litestar_vite.inertia.response._render_inertia_ssr",
            new_callable=AsyncMock,
            return_value=_InertiaSSRResult(
                head=["<title>SSR_TITLE_VUE</title>"],
                body='<div id="app">SSR_BODY_VUE</div>',
            ),
        ) as mock_ssr:
            with TestClient(app=module.app) as client:
                response = client.get("/")
        assert response.status_code == 200, response.text
        mock_ssr.assert_awaited_once()
        assert "SSR_BODY_VUE" in response.text
        assert "SSR_TITLE_VUE" in response.text
    finally:
        sys.modules.pop("_vue_inertia_ssr_example", None)


def test_vue_inertia_jinja_ssr_example_invokes_ssr_endpoint() -> None:
    """The vue-inertia-jinja-ssr example POSTs to the Inertia SSR endpoint and injects into the Jinja shell."""
    import importlib.util
    import sys
    from unittest.mock import AsyncMock, patch

    from litestar.testing import TestClient

    from litestar_vite.inertia.response import _InertiaSSRResult

    example_dir = EXAMPLES_ROOT / "vue-inertia-jinja-ssr"
    spec = importlib.util.spec_from_file_location("_vue_inertia_jinja_ssr_example", example_dir / "app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_vue_inertia_jinja_ssr_example"] = module
    try:
        spec.loader.exec_module(module)
        with patch(
            "litestar_vite.inertia.response._render_inertia_ssr",
            new_callable=AsyncMock,
            return_value=_InertiaSSRResult(
                head=["<title>SSR_TITLE_JINJA</title>"],
                body='<div id="app">SSR_BODY_JINJA</div>',
            ),
        ) as mock_ssr:
            with TestClient(app=module.app) as client:
                response = client.get("/")
        assert response.status_code == 200, response.text
        mock_ssr.assert_awaited_once()
        assert "SSR_BODY_JINJA" in response.text
        assert "SSR_TITLE_JINJA" in response.text
    finally:
        sys.modules.pop("_vue_inertia_jinja_ssr_example", None)


def test_htmx_no_jinja_example_starts_without_jinja_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The htmx-no-jinja example must boot cleanly when Jinja2 is treated as absent.

    This locks the C1 contract (template-mode-without-Jinja) at the example level —
    the example is the canonical demonstration that handlers returning raw HTML strings
    do not require a TemplateConfig or Jinja2 import.
    """
    import importlib.util
    import sys

    from litestar.testing import TestClient

    from litestar_vite.config import _vite

    monkeypatch.setattr(_vite, "JINJA_INSTALLED", False)

    example_dir = EXAMPLES_ROOT / "htmx-no-jinja"
    spec = importlib.util.spec_from_file_location("_htmx_no_jinja_example", example_dir / "app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_htmx_no_jinja_example"] = module
    try:
        spec.loader.exec_module(module)
        with TestClient(app=module.app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "hx-get" in response.text
    finally:
        sys.modules.pop("_htmx_no_jinja_example", None)


def test_templates_no_hardcoded_type_paths() -> None:
    """Ensure templates rely on cascading type paths (no explicit openapiPath/routesPath)."""
    forbidden = ("openapiPath", "routesPath", "schemaPath")
    for tmpl in TEMPLATE_ROOT.rglob("vite.config*.j2"):
        text = tmpl.read_text()
        for needle in forbidden:
            assert needle not in text, f"{needle} should be removed from template {tmpl}"
    nuxt_cfg_path = TEMPLATE_ROOT / "nuxt" / "nuxt.config.ts.j2"
    if nuxt_cfg_path.exists():
        nuxt_cfg = nuxt_cfg_path.read_text()
        assert all(n not in nuxt_cfg for n in forbidden)


def test_example_dev_scripts_are_framework_specific() -> None:
    astro = EXAMPLES_ROOT / "astro" / "package.json"
    nuxt = EXAMPLES_ROOT / "nuxt" / "package.json"
    if astro.exists():
        assert '"dev": "astro dev"' in astro.read_text()
    if nuxt.exists():
        assert '"dev": "nuxt dev"' in nuxt.read_text()


def test_inertia_examples_use_stable_script_element_bootstrap() -> None:
    """Ensure current examples target Inertia v3 while docs preserve the v2 path."""
    react_hybrid = (EXAMPLES_ROOT / "react-inertia" / "resources" / "main.tsx").read_text()
    vue_hybrid = (EXAMPLES_ROOT / "vue-inertia" / "resources" / "main.ts").read_text()
    react_jinja = (EXAMPLES_ROOT / "react-inertia-jinja" / "resources" / "main.tsx").read_text()
    vue_jinja = (EXAMPLES_ROOT / "vue-inertia-jinja" / "resources" / "main.ts").read_text()
    react_openapi = (EXAMPLES_ROOT / "react-inertia" / "openapi-ts.config.ts").read_text()
    react_jinja_openapi = (EXAMPLES_ROOT / "react-inertia-jinja" / "openapi-ts.config.ts").read_text()
    vue_openapi = (EXAMPLES_ROOT / "vue-inertia" / "openapi-ts.config.ts").read_text()
    vue_jinja_openapi = (EXAMPLES_ROOT / "vue-inertia-jinja" / "openapi-ts.config.ts").read_text()

    assert "@ts-expect-error" not in react_hybrid
    assert "@ts-expect-error" not in vue_hybrid
    assert "defaults: {" in react_hybrid
    assert 'import { csrfHeaders } from "litestar-vite-plugin/helpers"' in react_hybrid
    assert "visitOptions: (_href, options) => ({" in react_hybrid
    assert "headers: csrfHeaders(options.headers ?? {})," in react_hybrid
    assert "future: {" not in react_hybrid
    assert "useScriptElementForInitialPage: true" not in react_hybrid
    assert "defaults: {" in vue_hybrid
    assert 'import { csrfHeaders } from "litestar-vite-plugin/helpers"' in vue_hybrid
    assert "visitOptions: (_href, options) => ({" in vue_hybrid
    assert "headers: csrfHeaders(options.headers ?? {})," in vue_hybrid
    assert "future: {" not in vue_hybrid
    assert "useScriptElementForInitialPage: true" not in vue_hybrid

    assert "@ts-expect-error" not in react_jinja
    assert "@ts-expect-error" not in vue_jinja
    assert "defaults: {" in react_jinja
    assert 'import { csrfHeaders } from "litestar-vite-plugin/helpers"' in react_jinja
    assert "visitOptions: (_href, options) => ({" in react_jinja
    assert "headers: csrfHeaders(options.headers ?? {})," in react_jinja
    assert "future: {" not in react_jinja
    assert "useScriptElementForInitialPage: true" not in react_jinja
    assert "defaults: {" in vue_jinja
    assert 'import { csrfHeaders } from "litestar-vite-plugin/helpers"' in vue_jinja
    assert "visitOptions: (_href, options) => ({" in vue_jinja
    assert "headers: csrfHeaders(options.headers ?? {})," in vue_jinja
    assert "future: {" not in vue_jinja
    assert "useScriptElementForInitialPage: true" not in vue_jinja

    for text in (react_openapi, react_jinja_openapi, vue_openapi, vue_jinja_openapi):
        assert "@hey-api/client-axios" not in text
        assert "@hey-api/client-fetch" in text

    react_spa_openapi = (EXAMPLES_ROOT / "react" / "openapi-ts.config.ts").read_text()
    vue_spa_openapi = (EXAMPLES_ROOT / "vue" / "openapi-ts.config.ts").read_text()
    svelte_spa_openapi = (EXAMPLES_ROOT / "svelte" / "openapi-ts.config.ts").read_text()

    for text in (react_spa_openapi, vue_spa_openapi, svelte_spa_openapi):
        assert "@hey-api/client-axios" not in text
        assert "@hey-api/client-fetch" in text


def test_inertia_templates_do_not_use_stale_script_element_bootstrap() -> None:
    """Ensure generated templates avoid stale top-level script-element config."""
    react_template = (TEMPLATE_ROOT / "react-inertia" / "resources" / "main.tsx.j2").read_text()
    vue_template = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "main.ts.j2").read_text()
    react_ssr = (TEMPLATE_ROOT / "react-inertia" / "resources" / "ssr.tsx.j2").read_text()
    vue_ssr = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "ssr.ts.j2").read_text()

    for template in (react_template, vue_template, react_ssr, vue_ssr):
        assert "useScriptElementForInitialPage: true," not in template
        assert "Inertia v2" in template
        assert "Inertia v3" in template
        assert "defaults to the script-element bootstrap" in template
        assert "use_script_element=False" in template

    for template in (react_template, vue_template):
        assert "\n  defaults: {" in template
        assert 'import { csrfHeaders } from "litestar-vite-plugin/helpers";' in template
        assert "visitOptions: (_href, options) => ({" in template
        assert "headers: csrfHeaders(options.headers ?? {})," in template
        assert "cookie_httponly=True" in template

    for template in (react_ssr, vue_ssr):
        assert "\n  defaults: {" not in template

    assert "If you enable use_script_element=True" not in react_template
    assert "If you enable use_script_element=True" not in react_ssr
    assert "If you enable use_script_element=True" not in vue_template
    assert "If you enable use_script_element=True" not in vue_ssr


def test_inertia_jinja_templates_include_script_element_target() -> None:
    """Ensure manual Jinja script-element templates point back at the app root."""
    react_template = (EXAMPLES_ROOT / "react-inertia-jinja" / "templates" / "index.html").read_text()
    vue_template = (EXAMPLES_ROOT / "vue-inertia-jinja" / "templates" / "index.html").read_text()

    assert 'id="app_page" data-page="app"' in react_template
    assert 'id="app_page" data-page="app"' in vue_template


def test_inertia_docs_use_stable_script_element_bootstrap_path() -> None:
    """Ensure docs cover both the Inertia v2 and v3 script-element paths."""
    config_docs = (ROOT / "docs" / "frameworks" / "inertia" / "configuration.rst").read_text()
    ssr_docs = (ROOT / "docs" / "reference" / "inertia" / "ssr.rst").read_text()
    install_docs = (ROOT / "docs" / "frameworks" / "inertia" / "installation.rst").read_text()
    upgrade_docs = (ROOT / "docs" / "frameworks" / "inertia" / "upgrade-guide.rst").read_text()
    index_docs = (ROOT / "docs" / "frameworks" / "inertia" / "index.rst").read_text()
    inertia_config = (ROOT / "src" / "py" / "litestar_vite" / "config" / "_inertia.py").read_text()

    assert "defaults: {" in config_docs
    assert "Inertia v2" in config_docs
    assert "Inertia v3" in config_docs
    assert "Default: ``True``" in config_docs
    assert "useScriptElementForInitialPage: true" in config_docs
    assert "useScriptElementForInitialPage: true," not in config_docs.split("defaults: {", 1)[0]
    assert "defaults.future.useScriptElementForInitialPage" in ssr_docs
    assert "Inertia v2" in ssr_docs
    assert "Inertia v3" in ssr_docs
    assert "Node SSR entry" in ssr_docs
    assert "supports Inertia v2 and v3" in install_docs
    assert "upgrade-guide" in install_docs
    assert "upgrade-guide" in index_docs
    assert "supports Inertia v2 and v3" in upgrade_docs
    assert "defaults.future.useScriptElementForInitialPage" in upgrade_docs
    assert "Generated templates and examples now target Inertia v3" in upgrade_docs
    assert "Inertia v2" in inertia_config
    assert "Inertia v3" in inertia_config
    assert "use_script_element: bool = True" in inertia_config
    assert "useScriptElementForInitialPage: true" in inertia_config


def test_inertia_readme_and_llms_reference_stable_script_element_bootstrap() -> None:
    """Ensure repo-level docs mention the paired server/client script-element setup."""
    readme = (ROOT / "README.md").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    for text in (readme, llms_summary, llms_full):
        assert "use_script_element=False" in text
        assert "useScriptElementForInitialPage" in text


def test_readme_and_llms_reference_docs_theme_structure() -> None:
    """Ensure repo-level and maintainer docs point to the correct Shibuya theme overrides."""
    contributing = (ROOT / "CONTRIBUTING.rst").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    theme_markers = [
        "docs/conf.py",
        "docs/_static/theme.css",
        "docs/_static/layout.css",
        "docs/_static/code.css",
        "docs/_static/theme.js",
        "docs/_templates/components/copy-page-button.html",
    ]

    for text in (contributing, llms_summary, llms_full):
        for marker in theme_markers:
            assert marker in text, f"{marker} missing from docs/repo-level text"
        assert "Shibuya" in text
        assert "SQLSpec WASM playground" in text


def test_inertia_ssr_docs_cover_entry_files_and_bootstrap_interaction() -> None:
    """Ensure SSR docs explain the SSR entrypoint and script-element interaction."""
    ssr_docs = (ROOT / "docs" / "reference" / "inertia" / "ssr.rst").read_text()

    assert "resources/ssr.tsx" in ssr_docs
    assert "resources/ssr.ts" in ssr_docs
    assert "use_script_element" in ssr_docs
    assert "data-page" in ssr_docs
    assert "app_selector" in ssr_docs


def test_framework_docs_and_js_reference_current_domains_and_wording() -> None:
    """Ensure shared docs avoid stale framework URLs and version-marketing copy."""
    docs_index = (ROOT / "docs" / "index.rst").read_text()
    frameworks_index = (ROOT / "docs" / "frameworks" / "index.rst").read_text()
    sveltekit_docs = (ROOT / "docs" / "frameworks" / "sveltekit.rst").read_text()
    nuxt_docs = (ROOT / "docs" / "frameworks" / "nuxt.rst").read_text()
    readme = (ROOT / "README.md").read_text()
    dev_server = (ROOT / "src" / "js" / "src" / "dev-server" / "index.html").read_text()
    js_index = (ROOT / "src" / "js" / "src" / "index.ts").read_text()
    nuxt_module = (ROOT / "src" / "js" / "src" / "nuxt.ts").read_text()

    for text in (docs_index, dev_server, js_index):
        assert "vitejs.dev" not in text
        assert "vite.dev" in text

    assert "docs.litestar.dev/vite" not in js_index
    assert "litestar-org.github.io/litestar-vite/latest/" in js_index

    assert "kit.svelte.dev" not in sveltekit_docs
    assert "https://svelte.dev/docs/kit" in sveltekit_docs

    for text in (frameworks_index, readme, nuxt_docs, nuxt_module):
        assert "React 18+" not in text
        assert "Angular 18+" not in text
        assert "Nuxt 3+" not in text

    assert "new in v0.15" not in frameworks_index.lower()


def test_inertia_docs_use_current_links_and_protocol_headers() -> None:
    """Ensure Inertia docs use current canonical links and describe all supported request headers."""
    inertia_docs = ROOT / "docs" / "frameworks" / "inertia"
    load_when_visible = (inertia_docs / "load-when-visible.rst").read_text()
    once_props = (inertia_docs / "once-props.rst").read_text()
    polling = (inertia_docs / "polling.rst").read_text()
    prefetching = (inertia_docs / "prefetching.rst").read_text()
    remembering_state = (inertia_docs / "remembering-state.rst").read_text()
    how_it_works = (inertia_docs / "how-it-works.rst").read_text()
    partial_reloads = (inertia_docs / "partial-reloads.rst").read_text()
    configuration = (inertia_docs / "configuration.rst").read_text()
    fullstack_example = (inertia_docs / "fullstack-example.rst").read_text()

    for text in (load_when_visible, once_props, polling, prefetching, remembering_state):
        assert "inertiajs.com/docs/v2/data-props/" not in text

    assert "https://inertiajs.com/load-when-visible" in load_when_visible
    assert "https://inertiajs.com/once-props" in once_props
    assert "https://inertiajs.com/polling" in polling
    assert "https://inertiajs.com/prefetching" in prefetching
    assert "https://inertiajs.com/remembering-state" in remembering_state

    assert "app_page" in how_it_works
    assert 'data-page="app"' in how_it_works
    assert "X-Inertia-Except-Once-Props" in how_it_works
    assert "X-Inertia-Except-Once-Props" in partial_reloads
    assert "Starting in v0.15" not in configuration
    assert "(new in v0.15)" not in configuration
    assert "React 18" not in fullstack_example
    assert "Vue 3" not in fullstack_example
    assert "Svelte 5" not in fullstack_example


def test_angular_cli_example_uses_current_builder_and_tailwind_structure() -> None:
    """Ensure Angular CLI surfaces match the current builder and Tailwind setup."""
    angular_json = (EXAMPLES_ROOT / "angular-cli" / "angular.json").read_text()
    styles = (EXAMPLES_ROOT / "angular-cli" / "src" / "styles.css").read_text()
    index_html = (EXAMPLES_ROOT / "angular-cli" / "src" / "index.html").read_text()
    tsconfig_app = (EXAMPLES_ROOT / "angular-cli" / "tsconfig.app.json").read_text()

    assert "@angular/build:application" in angular_json
    assert "@angular/build:dev-server" in angular_json
    assert "@angular-devkit/build-angular" not in angular_json
    assert "src/generated" not in angular_json
    assert '"assets"' not in angular_json
    assert "@config" not in styles
    assert "favicon.ico" not in index_html
    assert "src/generated" not in tsconfig_app
    assert not (EXAMPLES_ROOT / "angular-cli" / "tailwind.config.js").exists()
    assert not (EXAMPLES_ROOT / "angular-cli" / "tsconfig.spec.json").exists()


def test_angular_cli_and_htmx_templates_match_current_owned_scaffolds() -> None:
    """Ensure owned templates drop stale Angular CLI/HTMX config patterns."""
    angular_cli_template = (TEMPLATE_ROOT / "angular-cli" / "package.json.j2").read_text()
    angular_cli_json = (TEMPLATE_ROOT / "angular-cli" / "angular.json.j2").read_text()
    angular_cli_styles = (TEMPLATE_ROOT / "angular-cli" / "src" / "styles.css.j2").read_text()
    htmx_base = (TEMPLATE_ROOT / "htmx" / "templates" / "base.html.j2.j2").read_text()
    htmx_index = (TEMPLATE_ROOT / "htmx" / "templates" / "index.html.j2.j2").read_text()

    assert '"latest"' not in angular_cli_template
    assert "@angular/build:application" in angular_cli_json
    assert "@angular/build:dev-server" in angular_cli_json
    assert "@angular-devkit/build-angular" not in angular_cli_json
    assert "src/generated" not in angular_cli_json
    assert "@config" not in angular_cli_styles
    assert not (TEMPLATE_ROOT / "angular-cli" / "tailwind.config.js.j2").exists()
    assert not (TEMPLATE_ROOT / "angular-cli" / "tsconfig.spec.json.j2").exists()

    assert 'meta name="csrf-token"' in htmx_base
    assert 'body hx-ext="litestar"' in htmx_base
    assert "color-scheme:" not in htmx_base
    assert "Load Greeting from API" in htmx_index


def test_angular_cli_and_htmx_docs_match_current_owned_scaffolds() -> None:
    """Ensure Angular CLI and HTMX docs reflect the updated scaffolds."""
    angular_docs = (ROOT / "docs" / "frameworks" / "angular.rst").read_text()
    htmx_docs = (ROOT / "docs" / "frameworks" / "htmx.rst").read_text()
    vite_docs = (ROOT / "docs" / "usage" / "vite.rst").read_text()

    assert "Angular application builder" in angular_docs
    assert "Manual script" in angular_docs
    assert "styles.css" in htmx_docs
    assert "registerHtmxExtension()" in htmx_docs
    assert "resources/" in vite_docs
    assert "litestar assets generate-types" in vite_docs


def test_angular_cli_owned_surfaces_drop_stale_zoneless_marketing_copy() -> None:
    """Ensure owned Angular CLI surfaces do not ship version-coupled marketing comments."""
    owned_files = [
        EXAMPLES_ROOT / "angular-cli" / "src" / "app" / "app.config.ts",
        EXAMPLES_ROOT / "angular-cli" / "src" / "app" / "home.component.ts",
        TEMPLATE_ROOT / "angular-cli" / "src" / "app" / "app.config.ts.j2",
    ]

    for path in owned_files:
        text = path.read_text()
        assert "zoneless" not in text


def test_svelte_templates_use_current_svelte_5_entrypoints() -> None:
    """Ensure Svelte templates use the Svelte 5 mount and props APIs."""
    svelte_main = (TEMPLATE_ROOT / "svelte" / "src" / "main.ts.j2").read_text()
    inertia_main = (TEMPLATE_ROOT / "svelte-inertia" / "resources" / "main.ts.j2").read_text()
    inertia_home = (TEMPLATE_ROOT / "svelte-inertia" / "resources" / "pages" / "Home.svelte.j2").read_text()

    assert "mount(App" in svelte_main
    assert "new App(" not in svelte_main
    assert "Root element #app not found" in svelte_main

    assert "mount(App" in inertia_main
    assert "new App(" not in inertia_main
    assert "props," in inertia_main

    assert "$props()" in inertia_home
    assert "export let" not in inertia_home


def test_sveltekit_templates_use_current_adapter_and_hooks() -> None:
    """Ensure the SvelteKit scaffold matches current adapter-node and hook patterns."""
    sveltekit_config = (TEMPLATE_ROOT / "sveltekit" / "svelte.config.js.j2").read_text()
    sveltekit_hooks = (TEMPLATE_ROOT / "sveltekit" / "src" / "hooks.server.ts.j2").read_text()
    sveltekit_layout = (TEMPLATE_ROOT / "sveltekit" / "src" / "routes" / "+layout.svelte.j2").read_text()

    assert "@sveltejs/adapter-node" in sveltekit_config
    assert "@sveltejs/adapter-auto" not in sveltekit_config

    assert "@ts-expect-error" not in sveltekit_hooks
    assert 'duplex?: "half"' in sveltekit_hooks
    assert 'headers.delete("host")' in sveltekit_hooks

    assert "LayoutProps" in sveltekit_layout
    assert "Snippet" not in sveltekit_layout


def test_svelte_manifests_pin_concrete_stable_versions() -> None:
    """Ensure Svelte-family examples and templates pin stable versions instead of latest tags."""
    svelte_example = (EXAMPLES_ROOT / "svelte" / "package.json").read_text()
    sveltekit_example = (EXAMPLES_ROOT / "sveltekit" / "package.json").read_text()
    svelte_template = (TEMPLATE_ROOT / "svelte" / "package.json.j2").read_text()
    svelte_inertia_template = (TEMPLATE_ROOT / "svelte-inertia" / "package.json.j2").read_text()
    sveltekit_template = (TEMPLATE_ROOT / "sveltekit" / "package.json.j2").read_text()

    for text in (svelte_example, sveltekit_example, svelte_template, svelte_inertia_template, sveltekit_template):
        assert '"latest"' not in text

    assert '"@inertiajs/svelte": "{{ package_version(\'@inertiajs/svelte\') }}"' in svelte_inertia_template
    assert '"axios"' not in svelte_inertia_template
    assert '"axios"' not in svelte_example
    assert '"axios"' not in svelte_template
    assert '"prepare": "svelte-kit sync"' in sveltekit_example
    assert '"check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"' in sveltekit_example


def test_sveltekit_example_uses_load_functions_and_current_helper_types() -> None:
    """Ensure the SvelteKit example uses load/PageProps/LayoutProps instead of client-only fetches."""
    page = (EXAMPLES_ROOT / "sveltekit" / "src" / "routes" / "+page.svelte").read_text()
    page_load = (EXAMPLES_ROOT / "sveltekit" / "src" / "routes" / "+page.ts").read_text()
    layout = (EXAMPLES_ROOT / "sveltekit" / "src" / "routes" / "+layout.svelte").read_text()
    hooks = (EXAMPLES_ROOT / "sveltekit" / "src" / "hooks.server.ts").read_text()

    assert "PageProps" in page
    assert "onMount" not in page
    assert "satisfies PageLoad" in page_load
    assert 'route("summary")' in page_load
    assert "LayoutProps" in layout
    assert "@ts-expect-error" not in hooks


def test_svelte_example_keeps_frontend_config_aligned_with_backend_type_exports() -> None:
    """Ensure the plain Svelte example keeps types auto enabled and avoids dead aliases."""
    vite_config = (EXAMPLES_ROOT / "svelte" / "vite.config.ts").read_text()
    svelte_template_vite = (TEMPLATE_ROOT / "svelte" / "vite.config.ts.j2").read_text()
    inertia_template_vite = (TEMPLATE_ROOT / "svelte-inertia" / "vite.config.ts.j2").read_text()

    assert 'types: "auto"' in vite_config
    assert '"@": "/' not in svelte_template_vite
    assert '"@": "/' not in inertia_template_vite
