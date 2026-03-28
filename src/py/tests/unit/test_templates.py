from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"
EXAMPLES_ROOT = ROOT / "examples"


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
    assert "defaults:" not in react_hybrid
    assert "future: {" not in react_hybrid
    assert "useScriptElementForInitialPage: true" not in react_hybrid
    assert "defaults:" not in vue_hybrid
    assert "future: {" not in vue_hybrid
    assert "useScriptElementForInitialPage: true" not in vue_hybrid

    assert "@ts-expect-error" not in react_jinja
    assert "@ts-expect-error" not in vue_jinja
    assert "defaults:" not in react_jinja
    assert "future: {" not in react_jinja
    assert "useScriptElementForInitialPage: true" not in react_jinja
    assert "defaults:" not in vue_jinja
    assert "future: {" not in vue_jinja
    assert "useScriptElementForInitialPage: true" not in vue_jinja

    for text in (react_openapi, react_jinja_openapi, vue_openapi, vue_jinja_openapi):
        assert "@hey-api/client-axios" not in text


def test_inertia_templates_do_not_use_stale_script_element_bootstrap() -> None:
    """Ensure generated templates avoid stale top-level script-element config."""
    react_template = (TEMPLATE_ROOT / "react-inertia" / "resources" / "main.tsx.j2").read_text()
    vue_template = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "main.ts.j2").read_text()
    react_ssr = (TEMPLATE_ROOT / "react-inertia" / "resources" / "ssr.tsx.j2").read_text()
    vue_ssr = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "ssr.ts.j2").read_text()

    for template in (react_template, vue_template, react_ssr, vue_ssr):
        assert "\n  defaults: {" not in template
        assert "useScriptElementForInitialPage: true," not in template
        assert "Inertia v2" in template
        assert "Inertia v3" in template

    assert "If you enable use_script_element=True" in react_template
    assert "If you enable use_script_element=True" in react_ssr
    assert "If you enable use_script_element=True" in vue_template
    assert "If you enable use_script_element=True" in vue_ssr


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
    assert "useScriptElementForInitialPage: true" in inertia_config


def test_inertia_readme_and_llms_reference_stable_script_element_bootstrap() -> None:
    """Ensure repo-level docs mention the paired server/client script-element setup."""
    readme = (ROOT / "README.md").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    for text in (readme, llms_summary, llms_full):
        assert "use_script_element" in text
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

    assert '"@inertiajs/svelte": "3.0.0"' in svelte_inertia_template
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
