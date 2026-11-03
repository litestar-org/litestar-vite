"""Verification gate for documentation build artifacts, budgets, and coverage."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zlib
from pathlib import Path

from litestar_vite.cli import vite_group
from tools.docs.generate_cli_docs import main as cli_docs_main
from tools.docs.generate_ts_docs import PAGE_ROUTING, collect_subpath_docs
from tools.docs.generate_ts_docs import main as ts_docs_main
from tools.docs.postbuild import DEFAULT_DOCS_DIR, DEFAULT_SITE_DIR, LEGACY_REDIRECTS, run_postbuild
from tools.docs.scan_public_docstrings import scan_package

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_REFERENCE_HTML_BYTES = 220 * 1024
MAX_REFERENCE_TOC_HEADINGS = 14

WARNING_PATTERN = re.compile(r"\b(WARNING|ERROR)\b")
TOC_HEADING_RE = re.compile(r"^#{2,3}\s+.+$", re.MULTILINE)


def _run_zensical_build(strict_warnings: bool) -> list[str]:
    """Run ``zensical build --clean`` and inspect output for warnings or errors."""
    errors: list[str] = []
    proc = subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--clean"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        errors.append(f"zensical build failed with exit code {proc.returncode}:\n{combined_output}")
        return errors

    if strict_warnings:
        errors.extend(
            f"Documentation build warning/error detected: {line.strip()}"
            for line in combined_output.splitlines()
            if WARNING_PATTERN.search(line)
        )
    return errors


def _verify_site_artifacts(site_dir: Path) -> list[str]:
    """Verify required top-level site files, objects.inv, llms-full.txt, and redirect stubs."""
    errors: list[str] = [
        f"Missing required site artifact: {required_artifact}"
        for required_artifact in ("objects.inv", "llms.txt", "llms-full.txt", ".nojekyll")
        if not (site_dir / required_artifact).exists()
    ]

    inv_path = site_dir / "objects.inv"
    if inv_path.exists():
        inv_bytes = inv_path.read_bytes()
        if not inv_bytes.startswith(b"# Sphinx inventory version 2\n"):
            errors.append("site/objects.inv does not have a valid Sphinx v2 header.")
        else:
            lines = inv_bytes.splitlines(keepends=True)
            decompressed = zlib.decompress(b"".join(lines[4:])).decode("utf-8")
            if "litestar_vite.config.ViteConfig" not in decompressed:
                errors.append("site/objects.inv is missing litestar_vite.config.ViteConfig.")

    llms_full = site_dir / "llms-full.txt"
    if llms_full.exists() and "--8<--" in llms_full.read_text(encoding="utf-8"):
        errors.append("site/llms-full.txt contains unexpanded --8<-- snippet directives.")

    if site_dir.exists() and inv_path.exists():
        errors.extend(
            f"Missing flat legacy redirect stub: {legacy_route}.html"
            for legacy_route in LEGACY_REDIRECTS
            if not (site_dir / f"{legacy_route}.html").exists()
        )
    return errors


def _verify_autodoc_coverage(docs_dir: Path) -> list[str]:
    """Verify CLI and TypeScript autodoc reference pages are up to date and complete."""
    errors: list[str] = []
    cli_ref_md = docs_dir / "reference" / "cli.md"
    if cli_ref_md.exists():
        if cli_docs_main(["--check"]) != 0:
            errors.append("docs/reference/cli.md is out of sync with generate_cli_docs.py --check.")
        cli_text = cli_ref_md.read_text(encoding="utf-8")
        errors.extend(
            f"CLI command 'litestar assets {cmd_name}' is missing from docs/reference/cli.md"
            for cmd_name in sorted(vite_group.commands)
            if f"`litestar assets {cmd_name}`" not in cli_text
        )

    ts_docs = collect_subpath_docs(REPO_ROOT)
    if len(ts_docs) != 18:
        errors.append(f"Expected 18 TypeScript subpaths, found {len(ts_docs)}")
    unique_ts_pages = sorted(set(PAGE_ROUTING.values()))
    existing_ts_pages = [REPO_ROOT / rel_path for rel_path in unique_ts_pages if (REPO_ROOT / rel_path).exists()]
    if existing_ts_pages:
        if ts_docs_main(["--check"]) != 0:
            errors.append("docs/reference/typescript/*.md is out of sync with generate_ts_docs.py --check.")
        all_ts_md = "\n".join(p.read_text(encoding="utf-8") for p in existing_ts_pages)
        errors.extend(
            f"TypeScript subpath {mod.import_specifier!r} missing from docs/reference/typescript/*.md"
            for mod in ts_docs
            if f"`{mod.import_specifier}`" not in all_ts_md
        )
    return errors


def _verify_reference_budgets(site_dir: Path, docs_dir: Path) -> list[str]:
    """Verify TOC heading count and compiled HTML byte budgets across reference pages."""
    errors: list[str] = []
    ref_dir = docs_dir / "reference"
    if ref_dir.exists():
        for md_file in sorted(ref_dir.rglob("*.md")):
            toc_headings = TOC_HEADING_RE.findall(md_file.read_text(encoding="utf-8"))
            if len(toc_headings) > MAX_REFERENCE_TOC_HEADINGS:
                errors.append(
                    f"{md_file.relative_to(docs_dir)} has {len(toc_headings)} TOC headings "
                    f"(max {MAX_REFERENCE_TOC_HEADINGS})"
                )

    site_ref_dir = site_dir / "reference"
    if site_ref_dir.exists():
        for html_file in sorted(site_ref_dir.rglob("*.html")):
            size_bytes = html_file.stat().st_size
            if size_bytes > MAX_REFERENCE_HTML_BYTES:
                errors.append(
                    f"{html_file.relative_to(site_dir)} is {size_bytes} bytes "
                    f"(exceeds {MAX_REFERENCE_HTML_BYTES} byte budget)"
                )
    return errors


def verify_docs_build(
    *,
    site_dir: Path = DEFAULT_SITE_DIR,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    run_build: bool = True,
    strict_warnings: bool = True,
) -> list[str]:
    """Verify all documentation build artifacts, coverage gates, and size budgets."""
    errors: list[str] = []

    if run_build:
        docstring_findings = scan_package()
        if docstring_findings:
            errors.append(f"scan_public_docstrings reported {len(docstring_findings)} finding(s).")
        errors.extend(_run_zensical_build(strict_warnings=strict_warnings))
        if errors:
            return errors
        run_postbuild(site_dir=site_dir, docs_dir=docs_dir)

    errors.extend(_verify_site_artifacts(site_dir))
    errors.extend(_verify_autodoc_coverage(docs_dir))
    errors.extend(_verify_reference_budgets(site_dir, docs_dir))
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``verify_docs_artifacts.py``."""
    parser = argparse.ArgumentParser(description="Verify documentation build and artifacts.")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        default=False,
        help="Fail if the documentation build emits any WARNING or ERROR log lines.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        default=False,
        help="Verify existing site/ artifacts without running zensical build.",
    )
    args = parser.parse_args(argv)

    errors = verify_docs_build(run_build=not args.no_build, strict_warnings=args.strict_warnings)
    if errors:
        for err in errors:
            sys.stderr.write(f"ERROR: {err}\n")
        return 1

    sys.stdout.write("Documentation verification passed with 0 errors.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
