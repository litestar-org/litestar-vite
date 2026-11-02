"""Unit tests for the public docstring and field hygiene scanner."""

from pathlib import Path

import pytest
from tools.docs.scan_public_docstrings import scan_package

REPO_ROOT = Path(__file__).resolve().parents[5]
PACKAGE_ROOT = REPO_ROOT / "src" / "py" / "litestar_vite"


def test_scan_detects_hybrid_attributes_missing_fields_overloads_and_rst(tmp_path: Path) -> None:
    """Verify scan_package flags hybrid Attributes, missing field docs, overload docs, and rST."""
    pkg = tmp_path / "sample_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "models.py").write_text(
        '"""Sample module."""\n\n'
        "from dataclasses import dataclass\n"
        "from typing import TypedDict, overload\n\n\n"
        "@dataclass\n"
        "class BadConfig:\n"
        '    """Config with duplicate Attributes section.\n\n'
        "    Attributes:\n"
        "        host: Hostname.\n"
        '    """\n\n'
        '    host: str = "localhost"\n'
        '    """Host address."""\n'
        "    port: int = 5173\n\n\n"
        "class BadHeaders(TypedDict):\n"
        '    """Headers TypedDict."""\n\n'
        "    x_inertia: str\n\n\n"
        "@overload\n"
        "def transform(val: int) -> int:\n"
        '    """Overload docstring that should be flagged."""\n'
        "    ...\n\n\n"
        "@overload\n"
        "def transform(val: str) -> str: ...\n\n\n"
        "def transform(val: int | str) -> int | str:\n"
        '    """Transform value.\n\n'
        "    .. warning::\n"
        "        Sphinx directive in docstring.\n"
        '    """\n'
        "    return val\n",
        encoding="utf-8",
    )

    findings = scan_package(pkg)
    kinds = {finding.kind for finding in findings}
    assert "missing-module-docstring" in kinds
    assert "hybrid-duplicate-attributes" in kinds
    assert "missing-field-docstring" in kinds
    assert "overload-has-docstring" in kinds
    assert "rst-directive-in-docstring" in kinds


def test_litestar_vite_public_docstrings_clean() -> None:
    """Verify 100% of src/py/litestar_vite passes public docstring and field hygiene checks."""
    findings = scan_package(PACKAGE_ROOT)
    if findings:
        formatted = "\n".join(f"{f.path}:{f.lineno} [{f.kind}] {f.symbol} - {f.message}" for f in findings)
        pytest.fail(f"Found {len(findings)} docstring hygiene violation(s):\n{formatted}")
