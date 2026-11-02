"""Tests for Zensical configuration, brand assets, Jinja overrides, and pyproject.toml metadata."""

from __future__ import annotations

import sys
import tokenize
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[5]


def _flatten_nav_paths(items: list[Any]) -> list[str]:
    paths: list[str] = []
    for item in items:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend(_flatten_nav_paths(value))
    return paths


def test_zensical_toml_configuration() -> None:
    """Verify zensical.toml configures Zensical Free, mkdocstrings-python, and the 43-page navigation tree."""
    zensical_path = REPO_ROOT / "zensical.toml"
    assert zensical_path.is_file(), "zensical.toml must exist at repository root"

    data = tomllib.loads(zensical_path.read_text(encoding="utf-8"))
    project = data["project"]
    assert project["site_name"] == "Litestar Vite"
    assert project["site_url"] == "https://litestar-org.github.io/litestar-vite/"
    assert "examples/**" in project["exclude_docs"]
    assert project["extra_css"] == ["stylesheets/extra.css"]
    assert project["extra"]["generator"] is False

    theme = project["theme"]
    assert theme["variant"] == "modern"
    assert theme["logo"] == "assets/logo.svg"
    assert theme["favicon"] == "assets/favicon.svg"
    assert "navigation.tabs" in theme["features"]
    assert "content.tabs.link" in theme["features"]
    assert "navigation.indexes" not in theme["features"]

    nav = project["nav"]
    assert len(nav) == 7
    top_tabs = [next(iter(section.keys())) for section in nav]
    assert top_tabs == [
        "Home",
        "Getting Started",
        "Core Concepts",
        "Frameworks & Inertia",
        "TypeGen & Realtime",
        "Architecture",
        "Reference",
    ]
    nav_paths = _flatten_nav_paths(nav)
    assert len(nav_paths) == 43
    assert len(set(nav_paths)) == 43

    mkdocstrings = project["plugins"]["mkdocstrings"]
    assert mkdocstrings["custom_templates"] == "tools/docs/templates"
    assert mkdocstrings["enable_inventory"] is True

    py_handler = mkdocstrings["handlers"]["python"]
    assert py_handler["paths"] == ["src/py"]
    py_opts = py_handler["options"]
    assert py_opts["docstring_style"] == "google"
    assert py_opts["docstring_section_style"] == "table"
    assert py_opts["merge_init_into_class"] is False
    assert py_opts["show_labels"] is False

    md_ext = project["markdown_extensions"]
    assert md_ext["toc"]["toc_depth"] == "2-3"
    assert md_ext["pymdownx"]["snippets"]["check_paths"] is True


def test_pyproject_doc_group_and_urls() -> None:
    """Verify pyproject.toml isolates the doc dependency group, fixes URLs, and excludes *.md from ruff format."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    urls = data["project"]["urls"]
    assert urls["Documentation"] == "https://litestar-org.github.io/litestar-vite/"
    assert urls["Homepage"] == "https://litestar-org.github.io/litestar-vite/"
    assert urls["Changelog"] == "https://litestar-org.github.io/litestar-vite/changelog/"

    dep_groups = data["dependency-groups"]
    assert "doc" in dep_groups
    assert "docs" not in dep_groups
    doc_deps = " ".join(dep_groups["doc"])
    assert "zensical>=0.0.71" in doc_deps
    assert "mkdocstrings-python>=2.0.1" in doc_deps
    assert "pymdown-extensions>=10.16" in doc_deps
    assert "ruff>=0.15.0" in doc_deps

    dev_includes = [item.get("include-group") for item in dep_groups["dev"] if isinstance(item, dict)]
    assert "doc" not in dev_includes
    assert "docs" not in dev_includes
    assert "types-docutils" not in dep_groups["linting"]

    ruff_format = data["tool"]["ruff"]["format"]
    assert "*.md" in ruff_format.get("exclude", [])


def test_branding_assets_and_jinja_templates_exist() -> None:
    """Verify official litestar-org/branding assets, extra.css, and mkdocstrings Jinja overrides exist."""
    required_assets = [
        "docs/stylesheets/extra.css",
        "docs/assets/logo.svg",
        "docs/assets/favicon.svg",
        "docs/assets/favicon.ico",
        "docs/assets/banner-inline-light.svg",
        "docs/assets/banner-inline-dark.svg",
        "docs/assets/og-social-light.svg",
        "docs/assets/og-social-dark.svg",
        "docs/assets/site.webmanifest",
        "tools/docs/__init__.py",
        "tools/docs/templates/python/material/attribute.html.jinja",
        "tools/docs/templates/python/material/docstring/attributes.html.jinja",
        "tools/docs/templates/python/material/summary/attributes.html.jinja",
    ]
    for rel_path in required_assets:
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Missing required documentation asset or template: {rel_path}"

    with (REPO_ROOT / "src/py/tests/unit/docs/test_toolchain_config.py").open("rb") as handle:
        comments = [tok for tok in tokenize.tokenize(handle.readline) if tok.type == tokenize.COMMENT]
    assert comments == []
