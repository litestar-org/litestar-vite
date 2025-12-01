from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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
