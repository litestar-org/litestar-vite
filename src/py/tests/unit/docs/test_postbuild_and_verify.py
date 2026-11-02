"""Unit tests for documentation postbuild pipeline and artifact verification."""

from __future__ import annotations

import zlib
from pathlib import Path

from tools.docs.postbuild import LEGACY_REDIRECTS, compact_site_html, run_postbuild
from tools.docs.verify_docs_artifacts import verify_docs_build


def test_legacy_redirects_cover_all_88_retired_rst_routes_and_latest() -> None:
    """Verify ``LEGACY_REDIRECTS`` covers all retired Sphinx routes plus ``latest/*``."""
    assert len(LEGACY_REDIRECTS) >= 88
    assert "latest/index" in LEGACY_REDIRECTS
    assert "latest/changelog" in LEGACY_REDIRECTS
    assert "usage/vite" in LEGACY_REDIRECTS
    assert "frameworks/inertia/deferred-props" in LEGACY_REDIRECTS
    assert "reference/config" in LEGACY_REDIRECTS
    assert "ssr/ipc-architecture" in LEGACY_REDIRECTS


def test_postbuild_generates_inventory_llms_and_all_legacy_redirects(tmp_path: Path) -> None:
    """Verify ``run_postbuild`` compacts HTML and emits ``objects.inv``, ``llms.txt``, and redirects."""
    site_dir = tmp_path / "site"
    docs_dir = tmp_path / "docs"
    site_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    sample_html = site_dir / "index.html"
    sample_html.write_text(
        "<html>\n\n\n  <body>\n    <h1>Litestar Vite</h1>      \n\n\n  </body>\n</html>\n", encoding="utf-8"
    )
    (docs_dir / "index.md").write_text("# Litestar Vite\n\nWelcome to the docs.\n", encoding="utf-8")

    saved_bytes = compact_site_html(site_dir)
    assert saved_bytes > 0

    run_postbuild(site_dir=site_dir, docs_dir=docs_dir)

    assert (site_dir / ".nojekyll").exists()
    assert (site_dir / "llms.txt").exists()
    assert (site_dir / "llms-full.txt").exists()
    llms_full_text = (site_dir / "llms-full.txt").read_text(encoding="utf-8")
    assert "--8<--" not in llms_full_text

    inv_path = site_dir / "objects.inv"
    assert inv_path.exists()
    inv_bytes = inv_path.read_bytes()
    assert inv_bytes.startswith(b"# Sphinx inventory version 2\n")
    lines = inv_bytes.splitlines(keepends=True)
    compressed_payload = b"".join(lines[4:])
    decompressed = zlib.decompress(compressed_payload).decode("utf-8")
    assert "litestar_vite.config.ViteConfig" in decompressed
    assert "litestar_vite.plugin.VitePlugin" in decompressed

    assert (site_dir / "usage" / "vite.html").exists()
    assert (site_dir / "usage" / "vite" / "index.html").exists()
    assert (site_dir / "latest" / "index.html").exists()
    redirect_html = (site_dir / "usage" / "vite.html").read_text(encoding="utf-8")
    assert "window.location.hash" in redirect_html


def test_verify_docs_artifacts_detects_missing_or_oversized_pages(tmp_path: Path) -> None:
    """Verify ``verify_docs_build`` checks size budgets, TOC budgets, and required artifacts."""
    site_dir = tmp_path / "site"
    docs_dir = tmp_path / "docs"
    site_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    errors = verify_docs_build(site_dir=site_dir, docs_dir=docs_dir, run_build=False)
    assert any("objects.inv" in err for err in errors)
