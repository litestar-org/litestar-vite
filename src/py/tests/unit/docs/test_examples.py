"""Unit tests for runnable documentation examples and conceptual guides."""

from __future__ import annotations

import importlib.util
import io
import sys
import tokenize
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
EXAMPLES_DIR = REPO_ROOT / "docs" / "examples"

EXPECTED_T05_EXAMPLES: tuple[str, ...] = (
    "getting_started/spa_app.py",
    "getting_started/inertia_app.py",
    "getting_started/template_app.py",
    "learn/vite_config_modes.py",
    "learn/static_props_app.py",
    "learn/islands_and_fragments.py",
    "learn/ssr_app.py",
    "learn/production_deploy.py",
)

EXPECTED_T05_GUIDES: tuple[str, ...] = (
    "docs/index.md",
    "docs/changelog.md",
    "docs/reference/contributing.md",
    "docs/getting-started/index.md",
    "docs/getting-started/quick-start-spa.md",
    "docs/getting-started/quick-start-inertia.md",
    "docs/getting-started/quick-start-templates.md",
    "docs/learn/index.md",
    "docs/learn/operating-modes.md",
    "docs/learn/configuration.md",
    "docs/learn/static-props.md",
    "docs/learn/islands-and-htmx.md",
    "docs/learn/ssr.md",
    "docs/learn/production-and-deploy.md",
    "docs/learn/doctor-and-troubleshooting.md",
)


def _discover_example_files() -> list[Path]:
    """Return all runnable example modules in ``docs/examples``."""
    if not EXAMPLES_DIR.exists():
        return []
    return sorted(path for path in EXAMPLES_DIR.rglob("*.py") if path.name != "__init__.py")


def _count_comment_tokens(path: Path) -> int:
    """Count ``tokenize.COMMENT`` tokens in a Python source file."""
    source = path.read_text(encoding="utf-8")
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return sum(1 for token in tokens if token.type == tokenize.COMMENT)


@pytest.mark.parametrize("rel_path", EXPECTED_T05_EXAMPLES)
def test_expected_example_modules_exist_and_run(rel_path: str) -> None:
    """Verify every required runnable example module has zero comments and runs ``main()``."""
    example_path = EXAMPLES_DIR / rel_path
    assert example_path.exists(), f"Missing example module: {rel_path}"
    assert _count_comment_tokens(example_path) == 0, f"Inline comments found in {rel_path}"

    module_name = "docs_example_" + rel_path.replace("/", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(module_name, example_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    exported = getattr(module, "__all__", ())
    assert "main" in exported, f"{rel_path} must export 'main' in __all__"
    main_fn = getattr(module, "main", None)
    assert callable(main_fn), f"{rel_path} must define callable main()"
    main_fn()


def test_all_discovered_examples_have_zero_comments_and_run() -> None:
    """Execute every discovered module under ``docs/examples/**/*.py``."""
    discovered = _discover_example_files()
    assert len(discovered) >= len(EXPECTED_T05_EXAMPLES)
    for example_path in discovered:
        rel_path = example_path.relative_to(EXAMPLES_DIR).as_posix()
        assert _count_comment_tokens(example_path) == 0, f"Inline comments found in {rel_path}"
        module_name = "docs_discovered_" + rel_path.replace("/", "_").removesuffix(".py")
        spec = importlib.util.spec_from_file_location(module_name, example_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        main_fn = getattr(module, "main", None)
        assert callable(main_fn), f"{rel_path} must define callable main()"
        main_fn()


@pytest.mark.parametrize("guide_rel_path", EXPECTED_T05_GUIDES)
def test_guide_pages_exist_and_omit_deprecated_proxy_mode(guide_rel_path: str) -> None:
    """Verify guide pages exist and never reference removed ``proxy_mode=\"direct\"``."""
    guide_path = REPO_ROOT / guide_rel_path
    assert guide_path.exists(), f"Missing guide page: {guide_rel_path}"
    content = guide_path.read_text(encoding="utf-8")
    assert 'proxy_mode="direct"' not in content
    assert "proxy_mode='direct'" not in content


def test_readme_uses_brand_banner_and_links_to_contributing() -> None:
    """Verify ``README.md`` uses the inline brand banner and stays concise."""
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "banner-inline-dark.svg" in readme_text
    assert "banner-inline-light.svg" in readme_text
    assert "docs/reference/contributing.md" in readme_text
    assert "/latest/" not in readme_text
