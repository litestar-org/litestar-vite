"""Unit tests for Python API reference pages and mkdocstrings directives."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

import litestar_vite
import litestar_vite.codegen
import litestar_vite.config
import litestar_vite.fragments
import litestar_vite.inertia
import litestar_vite.ipc
import litestar_vite.scaffolding

REPO_ROOT = Path(__file__).resolve().parents[5]
REFERENCE_DIR = REPO_ROOT / "docs" / "reference"

PYTHON_REFERENCE_PAGES: tuple[str, ...] = (
    "plugin-and-config.md",
    "inertia.md",
    "fragments-and-ipc.md",
    "runtime-and-assets.md",
    "tooling-and-codegen.md",
)

DIRECTIVE_RE = re.compile(r"^:::\s+(litestar_vite(?:\.[A-Za-z0-9_]+)+)\s*$", re.MULTILINE)
TOC_HEADING_RE = re.compile(r"^#{2,3}\s+.+$", re.MULTILINE)


def _resolve_dotted_symbol(dotted_path: str) -> object:
    """Resolve a dotted Python path via ``importlib`` and ``getattr``."""
    parts = dotted_path.split(".")
    for idx in range(len(parts), 0, -1):
        module_name = ".".join(parts[:idx])
        try:
            obj: object = importlib.import_module(module_name)
        except ImportError:
            continue
        for attr in parts[idx:]:
            obj = getattr(obj, attr)
        return obj
    msg = f"Cannot import module for directive target: {dotted_path}"
    raise ImportError(msg)


def test_reference_index_and_python_pages_exist() -> None:
    """Verify ``docs/reference/index.md`` and all 5 Python API reference pages exist."""
    assert (REFERENCE_DIR / "index.md").exists()
    for page_name in PYTHON_REFERENCE_PAGES:
        assert (REFERENCE_DIR / page_name).exists(), f"Missing reference page: {page_name}"


def test_all_public_python_exports_have_valid_mkdocstrings_directives() -> None:
    """Verify 100% of ``litestar_vite.__all__`` and subpackage exports resolve cleanly."""
    directives: list[str] = []
    for page_name in PYTHON_REFERENCE_PAGES:
        page_path = REFERENCE_DIR / page_name
        assert page_path.exists(), f"Missing reference page: {page_name}"
        content = page_path.read_text(encoding="utf-8")
        directives.extend(DIRECTIVE_RE.findall(content))

    assert directives, "No mkdocstrings directives found in Python reference pages"

    documented_short_names: set[str] = set()
    for target in directives:
        resolved = _resolve_dotted_symbol(target)
        assert resolved is not None
        documented_short_names.add(target.rsplit(".", 1)[-1])

    for root_symbol in litestar_vite.__all__:
        if root_symbol == "inertia":
            continue
        assert root_symbol in documented_short_names, (
            f"Root export {root_symbol!r} from litestar_vite.__all__ is missing from docs/reference/*.md"
        )

    subpackages = (
        litestar_vite.config,
        litestar_vite.inertia,
        litestar_vite.ipc,
        litestar_vite.fragments,
        litestar_vite.codegen,
        litestar_vite.scaffolding,
    )
    for subpkg in subpackages:
        for symbol in getattr(subpkg, "__all__", ()):
            if symbol == "helpers":
                continue
            assert symbol in documented_short_names, (
                f"Subpackage export {subpkg.__name__}.{symbol} is missing from docs/reference/*.md"
            )


@pytest.mark.parametrize("page_name", PYTHON_REFERENCE_PAGES)
def test_reference_pages_respect_toc_heading_budget(page_name: str) -> None:
    """Verify each Python reference page stays within the TOC heading budget."""
    page_path = REFERENCE_DIR / page_name
    assert page_path.exists(), f"Missing reference page: {page_name}"
    content = page_path.read_text(encoding="utf-8")
    toc_headings = TOC_HEADING_RE.findall(content)
    assert 1 <= len(toc_headings) <= 12, (
        f"{page_name} has {len(toc_headings)} H2/H3 headings (must be <= 12 to keep right TOC <= 14 items)"
    )
    directives = DIRECTIVE_RE.findall(content)
    assert len(directives) >= 5
    assert "heading_level: 4" in content
