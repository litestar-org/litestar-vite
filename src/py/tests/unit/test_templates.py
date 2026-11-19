import re
from pathlib import Path

import pytest
from jinja2 import Environment

from litestar_vite.scaffolding.generator import TemplateContext, render_template
from litestar_vite.scaffolding.templates import get_template

ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_ROOT = ROOT / "src" / "py" / "litestar_vite" / "templates"
EXAMPLES_ROOT = ROOT / "examples"


def _example_dir_names() -> set[str]:
    return {child.name for child in EXAMPLES_ROOT.iterdir() if child.is_dir() and (child / "app.py").exists()}


def test_framework_type_enum_includes_all_examples() -> None:
    """Every scaffold-backed example must have a matching FrameworkType value.

    Examples without enum entries are invisible to scaffolding lookups and risk
    drifting out of e2e parametrization. Proving-only examples opt out
    explicitly with a non-empty ``.scaffold-ignore`` explanation.
    """
    from litestar_vite.scaffolding.templates import FrameworkType

    enum_values = {ft.value for ft in FrameworkType}
    scaffold_examples = {
        name for name in _example_dir_names() if not (EXAMPLES_ROOT / name / ".scaffold-ignore").exists()
    }
    missing_in_enum = scaffold_examples - enum_values
    assert not missing_in_enum, f"Examples without FrameworkType entries: {missing_in_enum}"


def test_non_scaffold_examples_explain_their_classification() -> None:
    """A proving-only example must document why it is not a scaffold choice."""
    for name in _example_dir_names():
        marker = EXAMPLES_ROOT / name / ".scaffold-ignore"
        if marker.exists():
            assert marker.read_text().strip(), f"{name}: .scaffold-ignore must explain the classification"


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
    """vue-inertia-ssr and vue-inertia-jinja-ssr ship runnable dual-mode SSR entries.

    Each SSR example must have a ``resources/ssr.ts`` exporting ``render(page)`` for
    Vite's ``ModuleRunner`` in dev mode and starting the shared stdio worker for
    production, plus ``InertiaConfig(ssr=...)`` in ``app.py``.
    """
    for name in ("vue-inertia-ssr", "vue-inertia-jinja-ssr"):
        example = EXAMPLES_ROOT / name
        ssr_entry = example / "resources" / "ssr.ts"
        package_json = (example / "package.json").read_text()
        app_py = (example / "app.py").read_text()

        assert ssr_entry.exists(), f"{name}: missing resources/ssr.ts SSR runner entry"
        ssr_text = ssr_entry.read_text()
        assert "export default async function render" in ssr_text, (
            f"{name}: ssr.ts must export default async function render"
        )
        assert "@vue/server-renderer" in ssr_text, f"{name}: ssr.ts must import @vue/server-renderer"
        assert "startSsrWorker({ render })" in ssr_text, f"{name}: ssr.ts must start the shared production worker"

        assert "start:ssr" in package_json, f"{name}: package.json must define a start:ssr script"
        assert "build:ssr" in package_json, f"{name}: package.json must define a build:ssr script"
        assert "@vue/server-renderer" in package_json, f"{name}: package.json must include @vue/server-renderer"

        assert "InertiaConfig" in app_py and "ssr=" in app_py, f"{name}: app.py must construct InertiaConfig(ssr=...)"

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
                head=["<title>SSR_TITLE_VUE</title>"], body='<div id="app">SSR_BODY_VUE</div>'
            ),
        ) as mock_ssr:
            with TestClient(app=module.app) as client:
                response = client.get("/")
        assert response.status_code == 200, response.text
        mock_ssr.assert_awaited_once()
        assert "SSR_BODY_VUE" in response.text
        assert "SSR_TITLE_VUE" in response.text
        assert "{{ inertia" not in response.text
        assert "{{" not in response.text
        assert response.text.count('id="app_page"') == 1
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
                head=["<title>SSR_TITLE_JINJA</title>"], body='<div id="app">SSR_BODY_JINJA</div>'
            ),
        ) as mock_ssr:
            with TestClient(app=module.app) as client:
                response = client.get("/")
        assert response.status_code == 200, response.text
        mock_ssr.assert_awaited_once()
        assert "SSR_BODY_JINJA" in response.text
        assert "SSR_TITLE_JINJA" in response.text
        assert '<script type="application/json" id="app_page" data-page="app">' in response.text
        assert response.text.count('id="app_page"') == 1
        assert "{{ inertia" not in response.text
        assert "{{" not in response.text
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


def test_v3_inertia_shells_use_plain_title_tag() -> None:
    """Ensure Inertia shells use the canonical plain ``<title>`` tag.

    Per the Inertia v3 docs, the single ``<title>`` tag is always replaced by the
    client ``<Head>`` component and needs no marker attribute. The legacy
    ``inertia`` attribute (and its ``data-inertia`` successor) are only meaningful
    on keyed ``<meta>``/``<link>`` elements, never on the title.
    """
    paths = [
        TEMPLATE_ROOT / "react-inertia" / "index.html.j2",
        TEMPLATE_ROOT / "vue-inertia" / "index.html.j2",
        TEMPLATE_ROOT / "svelte-inertia" / "index.html.j2",
        EXAMPLES_ROOT / "react-inertia" / "index.html",
        EXAMPLES_ROOT / "react-inertia" / "resources" / "index.html",
        EXAMPLES_ROOT / "react-inertia-jinja" / "index.html",
        EXAMPLES_ROOT / "react-inertia-jinja" / "templates" / "index.html",
        EXAMPLES_ROOT / "vue-inertia" / "resources" / "index.html",
        EXAMPLES_ROOT / "vue-inertia-jinja" / "templates" / "index.html",
        EXAMPLES_ROOT / "vue-inertia-ssr" / "index.html",
        EXAMPLES_ROOT / "vue-inertia-jinja-ssr" / "templates" / "index.html",
        EXAMPLES_ROOT / "svelte-inertia" / "index.html",
        EXAMPLES_ROOT / "svelte-inertia-jinja" / "templates" / "index.html",
    ]

    for path in paths:
        text = path.read_text()
        assert "<title inertia>" not in text, f"{path} still uses the legacy Inertia title attribute"
        assert "<title data-inertia>" not in text, f"{path} marks the title with a superfluous data-inertia attribute"
        assert "<title>" in text, f"{path} is missing a plain <title> tag"


@pytest.mark.parametrize(
    ("relative_path", "required_markers", "forbidden_markers"),
    [
        (
            Path("react-inertia-jinja") / "templates" / "index.html",
            (
                '<div id="app"></div>',
                "{{ inertia_page }}",
                "{{ vite_hmr() }}",
                "{{ vite('resources/main.tsx') }}",
                "<title>react-inertia</title>",
            ),
            ("| safe", "|safe", "inertia | safe", "inertia|safe", 'id="app_page"'),
        ),
        (
            Path("vue-inertia-jinja") / "templates" / "index.html",
            (
                '<div id="app"></div>',
                "{{ inertia_page }}",
                "{{ vite_hmr() }}",
                "{{ vite('resources/main.ts') }}",
                "<title>vue-inertia</title>",
            ),
            ("| safe", "|safe", "inertia | safe", "inertia|safe", 'id="app_page"'),
        ),
        (
            Path("react-inertia-jinja") / "index.html",
            (
                '<div id="app"></div>',
                "<title>react-inertia</title>",
                '<script type="module" src="/resources/main.tsx"></script>',
            ),
            ("| safe", "|safe", "{{ inertia", 'id="app_page"', "data-page="),
        ),
        (
            Path("vue-inertia-jinja-ssr") / "templates" / "index.html",
            (
                '<div id="app"></div>',
                "{{ inertia_page }}",
                "{{ vite_hmr() }}",
                "{{ vite('resources/main.ts') }}",
                "<title>vue-inertia-jinja-ssr</title>",
            ),
            ("| safe", "|safe", "inertia | safe", "inertia|safe", 'id="app_page"'),
        ),
        (
            Path("svelte-inertia-jinja") / "templates" / "index.html",
            (
                '<div id="app"></div>',
                "{{ inertia_page }}",
                "{{ vite_hmr() }}",
                "{{ vite('resources/main.ts') }}",
                "<title>svelte-inertia-jinja</title>",
            ),
            ("| safe", "|safe", "inertia | safe", "inertia|safe", 'id="app_page"'),
        ),
    ],
    ids=[
        "react-inertia-jinja-template",
        "vue-inertia-jinja-template",
        "react-inertia-jinja-shell",
        "vue-inertia-jinja-ssr-template",
        "svelte-inertia-jinja-template",
    ],
)
def test_inertia_jinja_templates_include_script_element_target(
    relative_path: Path, required_markers: tuple[str, ...], forbidden_markers: tuple[str, ...]
) -> None:
    """Ensure Jinja Inertia examples use inertia_page and omit raw |safe output."""
    text = (EXAMPLES_ROOT / relative_path).read_text()

    if relative_path.parent.name == "templates":
        Environment(autoescape=True).parse(text)

    for marker in required_markers:
        assert marker in text, f"{relative_path} is missing expected marker: {marker}"
    for marker in forbidden_markers:
        assert marker not in text, f"{relative_path} still contains forbidden marker: {marker}"


@pytest.mark.parametrize(
    ("doc_path", "required_markers", "forbidden_markers"),
    [
        (
            ROOT / "docs" / "frameworks" / "inertia" / "configuration-and-templates.md",
            (
                '<div id="app"></div>',
                "{{ inertia_page }}",
                "inertia_page",
                'data-page="{{ inertia }}"',
                "useScriptElementForInitialPage: true",
            ),
            ("| safe", "|safe", "inertia | safe", "inertia|safe"),
        )
    ],
    ids=["inertia-configuration-and-templates"],
)
def test_inertia_template_docs_use_inertia_page_without_raw_safe_filter(
    doc_path: Path, required_markers: tuple[str, ...], forbidden_markers: tuple[str, ...]
) -> None:
    """Ensure Inertia template documentation teaches inertia_page without raw |safe output."""
    text = doc_path.read_text()

    for marker in required_markers:
        assert marker in text, f"{doc_path} is missing expected marker: {marker}"
    for marker in forbidden_markers:
        assert marker not in text, f"{doc_path} still contains forbidden marker: {marker}"


@pytest.mark.parametrize(
    ("surface_name", "paths"),
    [
        (
            "inertia-scaffolds",
            tuple(sorted(path for d in TEMPLATE_ROOT.glob("*-inertia") for path in d.rglob("*.html.j2"))),
        ),
        (
            "inertia-examples",
            tuple(
                sorted(
                    path
                    for d in EXAMPLES_ROOT.glob("*-inertia*")
                    for path in (d / "index.html", d / "resources" / "index.html", d / "templates" / "index.html")
                    if path.exists()
                )
            ),
        ),
        (
            "inertia-docs",
            tuple(
                sorted([
                    *(ROOT / "docs" / "frameworks" / "inertia").glob("*.md"),
                    ROOT / "docs" / "getting-started" / "quick-start-inertia.md",
                ])
            ),
        ),
    ],
    ids=["inertia-scaffolds", "inertia-examples", "inertia-docs"],
)
def test_inertia_surfaces_omit_raw_inertia_safe_filter(surface_name: str, paths: tuple[Path, ...]) -> None:
    """Verify zero raw {{ inertia | safe }} or {{ inertia|safe }} patterns remain across Inertia surfaces."""
    assert paths, f"Expected at least one file for {surface_name}"
    raw_safe_pattern = re.compile(r"\{\{\s*inertia\s*\|\s*safe\s*\}\}")
    for path in paths:
        text = path.read_text()
        assert not raw_safe_pattern.search(text), f"{path} still uses raw inertia | safe output"


@pytest.mark.parametrize(
    ("framework_name", "entry_asset"),
    [
        ("react-inertia", "resources/main.tsx"),
        ("vue-inertia", "resources/main.ts"),
        ("svelte-inertia", "resources/main.ts"),
    ],
)
def test_inertia_jinja_scaffold_templates_render_inertia_page_without_safe_filter(
    framework_name: str, entry_asset: str
) -> None:
    """Ensure Jinja Inertia scaffold templates render #app and inertia_page without |safe."""
    framework = get_template(framework_name)
    assert framework is not None

    template_path = TEMPLATE_ROOT / framework_name / "templates" / "index.html.j2"
    context = TemplateContext(project_name="demo-app", framework=framework).to_dict()
    rendered = render_template(template_path, context)

    Environment(autoescape=True).parse(rendered)

    assert "<title>demo-app</title>" in rendered
    assert "{{ vite_hmr() }}" in rendered
    assert f"{{{{ vite_asset('{entry_asset}') }}}}" in rendered
    assert '<div id="app"></div>' in rendered
    assert "{{ inertia_page }}" in rendered
    assert "inertia|safe" not in rendered
    assert "inertia | safe" not in rendered
    assert "|safe" not in rendered
    assert "| safe" not in rendered


@pytest.mark.parametrize(
    "shell_path",
    [
        TEMPLATE_ROOT / "svelte-inertia" / "index.html.j2",
        EXAMPLES_ROOT / "svelte-inertia" / "index.html",
        EXAMPLES_ROOT / "vue-inertia-ssr" / "index.html",
    ],
    ids=["svelte-inertia-template", "svelte-inertia-example", "vue-inertia-ssr-example"],
)
def test_hybrid_inertia_shells_omit_jinja_data_page_placeholders(shell_path: Path) -> None:
    """Ensure hybrid Inertia scaffold and example shells omit raw Jinja page placeholders."""
    text = shell_path.read_text()

    assert '<div id="app"></div>' in text
    assert '<script type="module"' in text
    assert "inertia | safe" not in text
    assert "inertia|safe" not in text
    assert "data-page=" not in text


@pytest.mark.parametrize(
    ("framework_name", "entry_asset"),
    [
        ("react-inertia", "resources/main.tsx"),
        ("vue-inertia", "resources/main.ts"),
        ("svelte-inertia", "resources/main.ts"),
    ],
)
def test_hybrid_inertia_scaffold_templates_render_plain_spa_shell(framework_name: str, entry_asset: str) -> None:
    """Ensure hybrid Inertia scaffold shells render clean SPA markup without Jinja tags."""
    framework = get_template(framework_name)
    assert framework is not None

    template_path = TEMPLATE_ROOT / framework_name / "index.html.j2"
    context = TemplateContext(project_name="demo-app", framework=framework).to_dict()
    rendered = render_template(template_path, context)

    assert "<title>demo-app</title>" in rendered
    assert '<div id="app"></div>' in rendered
    assert f'<script type="module" src="/{entry_asset}"></script>' in rendered
    assert "{{" not in rendered
    assert "data-page=" not in rendered
    assert "inertia | safe" not in rendered
    assert "inertia|safe" not in rendered


def test_inertia_docs_use_stable_script_element_bootstrap_path() -> None:
    """Ensure docs cover both the Inertia v2 and v3 script-element paths."""
    ssr_helpers = (ROOT / "docs" / "frameworks" / "inertia" / "ssr-and-typescript.md").read_text()
    config_templates = (ROOT / "docs" / "frameworks" / "inertia" / "configuration-and-templates.md").read_text()
    quickstart = (ROOT / "docs" / "getting-started" / "quick-start-inertia.md").read_text()
    doctor_docs = (ROOT / "docs" / "learn" / "doctor-and-troubleshooting.md").read_text()
    index_docs = (ROOT / "docs" / "frameworks" / "inertia" / "index.md").read_text()
    inertia_config = (ROOT / "src" / "py" / "litestar_vite" / "config" / "_inertia.py").read_text()

    assert "defaults: {" in ssr_helpers
    assert "Inertia.js" in ssr_helpers
    assert "Inertia v3" in ssr_helpers
    assert "useScriptElementForInitialPage: true" in ssr_helpers
    assert "useScriptElementForInitialPage: true" in config_templates
    assert "useScriptElementForInitialPage: true" in quickstart
    assert "InertiaConfig.use_script_element" in doctor_docs
    assert 'data-page="app"' in index_docs
    assert "Inertia" in inertia_config
    assert "use_script_element: bool = True" in inertia_config


def test_inertia_readme_and_llms_reference_stable_script_element_bootstrap() -> None:
    """Ensure repo-level docs mention the paired server/client script-element setup."""
    doctor_docs = (ROOT / "docs" / "learn" / "doctor-and-troubleshooting.md").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    for text in (doctor_docs, llms_summary, llms_full):
        assert "use_script_element" in text
        assert "useScriptElementForInitialPage" in text


def test_readme_and_llms_reference_docs_theme_structure() -> None:
    """Ensure repo-level and maintainer docs point to the correct documentation structure."""
    contributing = (ROOT / "CONTRIBUTING.rst").read_text()
    llms_summary = (ROOT / "llms.txt").read_text()
    llms_full = (ROOT / "llms-full.txt").read_text()

    theme_markers = ["zensical.toml", "docs/stylesheets/extra.css", "docs/assets/logo.svg", "docs/assets/favicon.svg"]

    for text in (contributing, llms_summary, llms_full):
        for marker in theme_markers:
            assert marker in text, f"{marker} missing from docs/repo-level text"


def test_inertia_ssr_docs_cover_entry_files_and_bootstrap_interaction() -> None:
    """Ensure SSR docs explain the SSR entrypoint and script-element interaction."""
    ssr_helpers = (ROOT / "docs" / "frameworks" / "inertia" / "ssr-and-typescript.md").read_text()
    ssr_concepts = (ROOT / "docs" / "learn" / "ssr.md").read_text()
    combined_docs = f"{ssr_helpers}\n{ssr_concepts}"

    assert "resources/ssr.tsx" in combined_docs
    assert "resources/ssr.ts" in combined_docs
    assert "use_script_element" in combined_docs
    assert "data-page" in combined_docs
    assert "app_selector" in combined_docs


def test_inertia_scaffolds_do_not_install_inertia_vite_plugin_by_default() -> None:
    """Ensure generated Inertia scaffolds keep litestar-vite-plugin as the bridge owner."""
    paths = [
        TEMPLATE_ROOT / "react-inertia" / "package.json.j2",
        TEMPLATE_ROOT / "vue-inertia" / "package.json.j2",
        TEMPLATE_ROOT / "svelte-inertia" / "package.json.j2",
        EXAMPLES_ROOT / "react-inertia" / "package.json",
        EXAMPLES_ROOT / "react-inertia-jinja" / "package.json",
        EXAMPLES_ROOT / "vue-inertia" / "package.json",
        EXAMPLES_ROOT / "vue-inertia-jinja" / "package.json",
        EXAMPLES_ROOT / "svelte-inertia" / "package.json",
        EXAMPLES_ROOT / "svelte-inertia-jinja" / "package.json",
    ]

    for path in paths:
        assert '"@inertiajs/vite"' not in path.read_text()


def test_framework_docs_and_js_reference_current_domains_and_wording() -> None:
    """Ensure shared docs avoid stale framework URLs and version-marketing copy."""
    docs_index = (ROOT / "docs" / "index.md").read_text()
    frameworks_index = (ROOT / "docs" / "frameworks" / "index.md").read_text()
    sveltekit_docs = (ROOT / "docs" / "frameworks" / "sveltekit.md").read_text()
    nuxt_docs = (ROOT / "docs" / "frameworks" / "nuxt.md").read_text()
    angular_docs = (ROOT / "docs" / "frameworks" / "angular.md").read_text()
    react_docs = (ROOT / "docs" / "frameworks" / "react.md").read_text()
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

    for text in (frameworks_index, readme, nuxt_docs, angular_docs, react_docs, nuxt_module):
        assert "React 18+" not in text
        assert "Angular 18+" not in text
        assert "Nuxt 3+" not in text

    assert "new in v0.15" not in frameworks_index.lower()


def test_inertia_docs_use_current_links_and_protocol_headers() -> None:
    """Ensure Inertia docs use current canonical links and describe all supported request headers."""
    inertia_docs = ROOT / "docs" / "frameworks" / "inertia"
    all_inertia_docs = "\n".join(p.read_text() for p in sorted(inertia_docs.glob("*.md")))

    assert "inertiajs.com" in all_inertia_docs
    assert "X-Inertia" in all_inertia_docs
    assert "X-Inertia-Version" in all_inertia_docs
    assert "X-Inertia-Partial-Data" in all_inertia_docs
    assert "X-Inertia-Partial-Component" in all_inertia_docs
    assert "X-Inertia-Location" in all_inertia_docs


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
    angular_docs = (ROOT / "docs" / "frameworks" / "angular.md").read_text()
    htmx_docs = (ROOT / "docs" / "frameworks" / "htmx.md").read_text()
    islands_docs = (ROOT / "docs" / "learn" / "islands-and-htmx.md").read_text()
    typegen_docs = (ROOT / "docs" / "typegen" / "openapi-sdk.md").read_text()

    assert "Angular CLI" in angular_docs
    assert "registerHtmxExtension()" in htmx_docs
    assert "registerHtmxExtension()" in islands_docs
    assert "litestar assets generate-types" in typegen_docs


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
    sveltekit_config = (TEMPLATE_ROOT / "sveltekit" / "vite.config.ts.j2").read_text()
    sveltekit_hooks = (TEMPLATE_ROOT / "sveltekit" / "src" / "hooks.server.ts.j2").read_text()
    sveltekit_layout = (TEMPLATE_ROOT / "sveltekit" / "src" / "routes" / "+layout.svelte.j2").read_text()

    assert "@sveltejs/adapter-node" in sveltekit_config
    assert "@sveltejs/adapter-auto" not in sveltekit_config
    assert not (TEMPLATE_ROOT / "sveltekit" / "svelte.config.js.j2").exists()

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
