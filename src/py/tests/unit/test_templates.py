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
        assert '"dev": "nuxi dev"' in nuxt.read_text()


def test_inertia_examples_use_stable_script_element_bootstrap() -> None:
    """Ensure Inertia examples match stable 2.3.x bootstrap guidance."""
    react_hybrid = (EXAMPLES_ROOT / "react-inertia" / "resources" / "main.tsx").read_text()
    vue_hybrid = (EXAMPLES_ROOT / "vue-inertia" / "resources" / "main.ts").read_text()
    react_jinja = (EXAMPLES_ROOT / "react-inertia-jinja" / "resources" / "main.tsx").read_text()
    vue_jinja = (EXAMPLES_ROOT / "vue-inertia-jinja" / "resources" / "main.ts").read_text()

    assert "@ts-expect-error" not in react_hybrid
    assert "@ts-expect-error" not in vue_hybrid
    assert "defaults:" in react_hybrid
    assert "future: {" in react_hybrid
    assert "useScriptElementForInitialPage: true" in react_hybrid
    assert "defaults:" in vue_hybrid
    assert "future: {" in vue_hybrid
    assert "useScriptElementForInitialPage: true" in vue_hybrid

    assert "@ts-expect-error" not in react_jinja
    assert "@ts-expect-error" not in vue_jinja
    assert "useScriptElementForInitialPage" not in react_jinja
    assert "useScriptElementForInitialPage" not in vue_jinja


def test_inertia_templates_do_not_use_stale_script_element_bootstrap() -> None:
    """Ensure generated templates avoid stale top-level script-element config."""
    react_template = (TEMPLATE_ROOT / "react-inertia" / "resources" / "main.tsx.j2").read_text()
    vue_template = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "main.ts.j2").read_text()
    react_ssr = (TEMPLATE_ROOT / "react-inertia" / "resources" / "ssr.tsx.j2").read_text()
    vue_ssr = (TEMPLATE_ROOT / "vue-inertia" / "resources" / "ssr.ts.j2").read_text()

    for template in (react_template, vue_template, react_ssr, vue_ssr):
        assert "useScriptElementForInitialPage: true," not in template


def test_inertia_docs_use_stable_script_element_bootstrap_path() -> None:
    """Ensure docs reference the stable defaults.future bootstrap path."""
    config_docs = (ROOT / "docs" / "inertia" / "configuration.rst").read_text()

    assert "defaults: {" in config_docs
    assert "future: {" in config_docs
    assert "useScriptElementForInitialPage: true" in config_docs
    assert "useScriptElementForInitialPage: true," not in config_docs.split("defaults: {", 1)[0]


def test_inertia_readme_and_llms_reference_stable_script_element_bootstrap() -> None:
    """Ensure repo-level docs mention the paired server/client script-element setup."""
    readme = (ROOT / "README.md").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    for text in (readme, llms_summary, llms_full):
        assert "use_script_element" in text
        assert "useScriptElementForInitialPage" in text


def test_inertia_ssr_docs_cover_entry_files_and_bootstrap_interaction() -> None:
    """Ensure SSR docs explain the SSR entrypoint and script-element interaction."""
    ssr_docs = (ROOT / "docs" / "reference" / "inertia" / "ssr.rst").read_text()

    assert "resources/ssr.tsx" in ssr_docs
    assert "resources/ssr.ts" in ssr_docs
    assert "use_script_element" in ssr_docs
    assert "data-page" in ssr_docs
    assert "app_selector" in ssr_docs
