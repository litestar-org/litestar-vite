"""Post-build pipeline for documentation artifacts and legacy redirects."""

from __future__ import annotations

import importlib
import inspect
import posixpath
import re
import sys
import zlib
from pathlib import Path

from msgspec import Struct

import litestar_vite
import litestar_vite.codegen
import litestar_vite.config
import litestar_vite.deploy
import litestar_vite.doctor
import litestar_vite.exceptions
import litestar_vite.executor
import litestar_vite.fragments
import litestar_vite.handler
import litestar_vite.inertia
import litestar_vite.ipc
import litestar_vite.loader
import litestar_vite.plugin
import litestar_vite.scaffolding

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SITE_DIR = REPO_ROOT / "site"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs"
SITE_URL = "https://litestar-org.github.io/litestar-vite"

SNIPPET_INCLUDE_RE = re.compile(r'^(\s*)--8<--\s+"([^"]+)"\s*$', re.MULTILINE)
DIRECTIVE_RE = re.compile(r"^:::\s+(litestar_vite(?:\.[A-Za-z0-9_]+)+)\s*$", re.MULTILINE)
PRE_BLOCK_RE = re.compile(r"(<pre\b[^>]*>.*?</pre>)", re.DOTALL | re.IGNORECASE)
LEADING_INDENT_RE = re.compile(r"\n[ \t]+")
MULTI_BLANK_LINES_RE = re.compile(r"\n\s*\n+")
TRAILING_WS_RE = re.compile(r"[ \t]+\n")

LEGACY_REDIRECTS: dict[str, str] = {
    "index": "index.html",
    "changelog": "changelog/",
    "contribution-guide": "reference/contributing/",
    "latest/index": "index.html",
    "latest/changelog": "changelog/",
    "usage/index": "getting-started/",
    "usage/vite": "learn/configuration/",
    "usage/modes": "learn/operating-modes/",
    "usage/development": "learn/development-and-proxy/",
    "usage/production": "learn/production-and-deploy/",
    "usage/static-props": "learn/static-props/",
    "usage/types": "typegen/",
    "usage/streams": "typegen/event-streams/",
    "guide/vite-architecture": "architecture/",
    "ssr/ipc-architecture": "architecture/ssr-and-ipc/",
    "hypermedia/fragments": "learn/islands-and-htmx/",
    "migration/0.33": "learn/migration-0-33/",
    "migration/0.32": "learn/migration-0-32/",
    "frameworks/index": "frameworks/",
    "frameworks/react": "frameworks/react/",
    "frameworks/vue": "frameworks/vue/",
    "frameworks/svelte": "frameworks/svelte/",
    "frameworks/htmx": "frameworks/htmx/",
    "frameworks/astro": "frameworks/astro/",
    "frameworks/nuxt": "frameworks/nuxt/",
    "frameworks/sveltekit": "frameworks/sveltekit/",
    "frameworks/angular": "frameworks/angular/",
    "frameworks/inertia/index": "frameworks/inertia/",
    "frameworks/inertia/how-it-works": "frameworks/inertia/",
    "frameworks/inertia/installation": "getting-started/quick-start-inertia/",
    "frameworks/inertia/configuration": "frameworks/inertia/configuration-and-templates/",
    "frameworks/inertia/pages": "frameworks/inertia/pages-and-responses/",
    "frameworks/inertia/responses": "frameworks/inertia/pages-and-responses/",
    "frameworks/inertia/routing": "frameworks/inertia/routing-and-links/",
    "frameworks/inertia/redirects": "frameworks/inertia/routing-and-links/",
    "frameworks/inertia/links": "frameworks/inertia/routing-and-links/",
    "frameworks/inertia/history-encryption": "frameworks/inertia/security-and-versioning/",
    "frameworks/inertia/asset-versioning": "frameworks/inertia/security-and-versioning/",
    "frameworks/inertia/templates": "frameworks/inertia/configuration-and-templates/",
    "frameworks/inertia/partial-reloads": "frameworks/inertia/partial-reloads-and-deferred/",
    "frameworks/inertia/deferred-props": "frameworks/inertia/partial-reloads-and-deferred/",
    "frameworks/inertia/merging-props": "frameworks/inertia/merging-and-infinite-scroll/",
    "frameworks/inertia/infinite-scroll": "frameworks/inertia/merging-and-infinite-scroll/",
    "frameworks/inertia/once-props": "frameworks/inertia/partial-reloads-and-deferred/",
    "frameworks/inertia/load-when-visible": "frameworks/inertia/partial-reloads-and-deferred/",
    "frameworks/inertia/polling": "frameworks/inertia/client-visits/",
    "frameworks/inertia/prefetching": "frameworks/inertia/client-visits/",
    "frameworks/inertia/remembering-state": "frameworks/inertia/client-visits/",
    "frameworks/inertia/shared-data": "frameworks/inertia/shared-data-and-flash/",
    "frameworks/inertia/shared-props-typing": "frameworks/inertia/shared-data-and-flash/",
    "frameworks/inertia/flash-data": "frameworks/inertia/shared-data-and-flash/",
    "frameworks/inertia/forms": "frameworks/inertia/forms-and-validation/",
    "frameworks/inertia/file-uploads": "frameworks/inertia/file-uploads/",
    "frameworks/inertia/validation": "frameworks/inertia/forms-and-validation/",
    "frameworks/inertia/error-handling": "frameworks/inertia/forms-and-validation/",
    "frameworks/inertia/precognition": "frameworks/inertia/forms-and-validation/",
    "frameworks/inertia/csrf-protection": "frameworks/inertia/security-and-versioning/",
    "frameworks/inertia/typescript": "frameworks/inertia/ssr-and-typescript/",
    "frameworks/inertia/type-generation": "frameworks/inertia/ssr-and-typescript/",
    "frameworks/inertia/typed-page-props": "frameworks/inertia/ssr-and-typescript/",
    "frameworks/inertia/fullstack-example": "getting-started/quick-start-inertia/",
    "frameworks/inertia/upgrade-guide": "frameworks/inertia/ssr-and-typescript/",
    "realtime/index": "typegen/realtime-channels/",
    "realtime/channels": "typegen/realtime-channels/",
    "realtime/websockets": "typegen/realtime-channels/",
    "realtime/sse": "typegen/realtime-channels/",
    "realtime/typegen": "typegen/realtime-channels/",
    "realtime/frameworks": "typegen/event-streams/",
    "realtime/browser-helpers": "typegen/event-streams/",
    "reference/index": "reference/",
    "reference/plugin": "reference/plugin-and-config/",
    "reference/config": "reference/plugin-and-config/",
    "reference/inertia/index": "reference/inertia/",
    "reference/inertia/plugin": "reference/inertia/",
    "reference/inertia/config": "reference/plugin-and-config/",
    "reference/inertia/request": "reference/inertia/",
    "reference/inertia/response": "reference/inertia/",
    "reference/inertia/middleware": "reference/inertia/",
    "reference/inertia/helpers": "reference/inertia/",
    "reference/inertia/exception_handler": "reference/inertia/",
    "reference/inertia/ssr": "reference/fragments-and-ipc/",
    "reference/inertia/types": "reference/inertia/",
    "reference/fragments": "reference/fragments-and-ipc/",
    "reference/ipc": "reference/fragments-and-ipc/",
    "reference/loader": "reference/runtime-and-assets/",
    "reference/spa": "reference/runtime-and-assets/",
    "reference/html_transform": "reference/runtime-and-assets/",
    "reference/exceptions": "reference/runtime-and-assets/",
    "reference/codegen": "reference/tooling-and-codegen/",
    "reference/deploy": "reference/tooling-and-codegen/",
    "reference/cli": "reference/cli/",
}


class InventoryEntry(Struct, frozen=True, gc=False):
    """Single Sphinx objects.inv v2 entry."""

    name: str
    domain_role: str
    priority: int
    uri: str
    dispname: str = "-"


def compact_site_html(site_dir: Path = DEFAULT_SITE_DIR) -> int:
    """Compact redundant blank lines and trailing whitespace outside ``<pre>`` blocks."""
    total_saved = 0
    for html_file in sorted(site_dir.rglob("*.html")):
        raw = html_file.read_text(encoding="utf-8")
        parts = PRE_BLOCK_RE.split(raw)
        compacted_parts: list[str] = []
        for idx, segment in enumerate(parts):
            if idx % 2 == 1:
                compacted_parts.append(segment)
            else:
                cleaned = TRAILING_WS_RE.sub("\n", segment)
                cleaned = LEADING_INDENT_RE.sub("\n", cleaned)
                cleaned = MULTI_BLANK_LINES_RE.sub("\n", cleaned)
                compacted_parts.append(cleaned)
        compacted = "".join(compacted_parts)
        saved = len(raw.encode("utf-8")) - len(compacted.encode("utf-8"))
        if saved > 0:
            html_file.write_text(compacted, encoding="utf-8")
            total_saved += saved
    return total_saved


def _resolve_dotted(dotted_path: str) -> object | None:
    """Resolve a dotted Python symbol for inventory classification."""
    parts = dotted_path.split(".")
    for idx in range(len(parts), 0, -1):
        mod_name = ".".join(parts[:idx])
        try:
            obj: object = importlib.import_module(mod_name)
        except ImportError:
            continue
        for attr in parts[idx:]:
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj
    return None


def _classify_role(obj: object) -> str:
    """Classify a Python object into a Sphinx domain:role."""
    if inspect.ismodule(obj):
        return "py:module"
    if inspect.isclass(obj):
        if issubclass(obj, BaseException):
            return "py:exception"
        return "py:class"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj) or callable(obj):
        return "py:function"
    return "py:data"


def _collect_inventory_entries(docs_dir: Path) -> list[InventoryEntry]:
    """Collect Sphinx inventory entries from ``docs/reference/*.md`` directives."""
    entries: dict[str, InventoryEntry] = {}
    ref_pages = (
        ("plugin-and-config.md", "reference/plugin-and-config/"),
        ("inertia.md", "reference/inertia/"),
        ("fragments-and-ipc.md", "reference/fragments-and-ipc/"),
        ("runtime-and-assets.md", "reference/runtime-and-assets/"),
        ("tooling-and-codegen.md", "reference/tooling-and-codegen/"),
    )

    default_targets: tuple[tuple[str, str], ...] = (
        ("litestar_vite.plugin.VitePlugin", "reference/plugin-and-config/"),
        ("litestar_vite.config.ViteConfig", "reference/plugin-and-config/"),
        ("litestar_vite.config.PathConfig", "reference/plugin-and-config/"),
        ("litestar_vite.config.RuntimeConfig", "reference/plugin-and-config/"),
        ("litestar_vite.config.InertiaConfig", "reference/plugin-and-config/"),
        ("litestar_vite.config.TypeGenConfig", "reference/plugin-and-config/"),
        ("litestar_vite.config.DeployConfig", "reference/plugin-and-config/"),
        ("litestar_vite.inertia.InertiaPlugin", "reference/inertia/"),
        ("litestar_vite.inertia.InertiaResponse", "reference/inertia/"),
        ("litestar_vite.fragments.FragmentEngine", "reference/fragments-and-ipc/"),
        ("litestar_vite.fragments.ComponentResponse", "reference/fragments-and-ipc/"),
        ("litestar_vite.loader.ViteAssetLoader", "reference/runtime-and-assets/"),
    )

    for dotted, page_uri in default_targets:
        obj = _resolve_dotted(dotted)
        role = _classify_role(obj) if obj is not None else "py:class"
        entries[dotted] = InventoryEntry(name=dotted, domain_role=role, priority=1, uri=f"{page_uri}#{dotted}")

    for filename, page_uri in ref_pages:
        page_path = docs_dir / "reference" / filename
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8")
        for dotted in DIRECTIVE_RE.findall(content):
            obj = _resolve_dotted(dotted)
            role = _classify_role(obj) if obj is not None else "py:class"
            entries[dotted] = InventoryEntry(name=dotted, domain_role=role, priority=1, uri=f"{page_uri}#{dotted}")
            short_name = dotted.rsplit(".", 1)[-1]
            if short_name in litestar_vite.__all__:
                root_dotted = f"litestar_vite.{short_name}"
                entries.setdefault(
                    root_dotted,
                    InventoryEntry(name=root_dotted, domain_role=role, priority=1, uri=f"{page_uri}#{dotted}"),
                )

    return sorted(entries.values(), key=lambda item: item.name)


def build_objects_inv(site_dir: Path = DEFAULT_SITE_DIR, docs_dir: Path = DEFAULT_DOCS_DIR) -> Path:
    """Write a Sphinx v2 ``objects.inv`` file to ``site/objects.inv``."""
    entries = _collect_inventory_entries(docs_dir)
    header = (
        b"# Sphinx inventory version 2\n"
        b"# Project: litestar-vite\n"
        b"# Version: 0.32.0\n"
        b"# The remainder of this file is compressed using zlib.\n"
    )
    payload_lines = [f"{e.name} {e.domain_role} {e.priority} {e.uri} {e.dispname}\n" for e in entries]
    compressed = zlib.compress("".join(payload_lines).encode("utf-8"), level=9)
    inv_path = site_dir / "objects.inv"
    inv_path.write_bytes(header + compressed)
    return inv_path


def _expand_snippets(markdown_text: str) -> str:
    """Expand ``--8<-- "path"`` snippet directives into inline file contents."""

    def _replace(match: re.Match[str]) -> str:
        indent = match.group(1)
        rel_path = match.group(2)
        target = REPO_ROOT / rel_path
        if not target.exists():
            return f"{indent}[Included file: {rel_path}]"
        if target.suffix == ".html":
            return f"{indent}[Interactive Architecture Diagram: {target.name}]"
        body = target.read_text(encoding="utf-8").rstrip()
        return "\n".join(f"{indent}{line}" if line else "" for line in body.splitlines())

    return SNIPPET_INCLUDE_RE.sub(_replace, markdown_text)


def build_llms_files(site_dir: Path = DEFAULT_SITE_DIR, docs_dir: Path = DEFAULT_DOCS_DIR) -> tuple[Path, Path]:
    """Generate ``site/llms.txt`` and ``site/llms-full.txt``."""
    llms_index_lines = [
        "# Litestar Vite",
        "",
        "> First-class Vite 7+, Inertia.js v2, Server-Rendered Islands, and End-to-End Type Generation for Litestar.",
        "",
        "## Documentation Index",
        "",
    ]

    full_sections: list[str] = ["# Litestar Vite — Complete Documentation Corpus", ""]

    md_files = sorted(docs_dir.rglob("*.md"))
    for md_path in md_files:
        rel_md = md_path.relative_to(docs_dir).as_posix()
        raw_md = md_path.read_text(encoding="utf-8")
        expanded_md = _expand_snippets(raw_md)
        title_match = re.search(r"^#\s+(.+)$", expanded_md, re.MULTILINE) or re.search(
            r"^title:\s*(.+)$", expanded_md, re.MULTILINE
        )
        title = title_match.group(1).strip().strip("\"'") if title_match else rel_md
        if rel_md == "index.md":
            url_path = ""
        elif rel_md.endswith("/index.md"):
            url_path = rel_md.removesuffix("index.md")
        else:
            url_path = rel_md.removesuffix(".md") + "/"
        llms_index_lines.append(f"- [{title}]({SITE_URL}/{url_path})")
        full_sections.append(f"---\n\n<!-- Source: docs/{rel_md} -->\n\n{expanded_md.strip()}\n")

    llms_txt_path = site_dir / "llms.txt"
    llms_full_path = site_dir / "llms-full.txt"
    llms_txt_path.write_text("\n".join(llms_index_lines).strip() + "\n", encoding="utf-8")
    llms_full_path.write_text("\n".join(full_sections).strip() + "\n", encoding="utf-8")
    return llms_txt_path, llms_full_path


def _render_redirect_html(from_html_rel: str, target_rel: str) -> str:
    """Render a hash-preserving HTML redirect stub."""
    from_dir = posixpath.dirname(from_html_rel)
    rel_target = posixpath.relpath(target_rel, start=from_dir or ".")
    if target_rel.endswith("/") and not rel_target.endswith("/"):
        rel_target += "/"
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f'  <meta http-equiv="refresh" content="0; url={rel_target}">\n'
        f'  <link rel="canonical" href="{SITE_URL}/{target_rel.lstrip("/")}">\n'
        "  <title>Redirecting...</title>\n"
        "  <script>\n"
        f'    window.location.replace("{rel_target}" + (window.location.hash || ""));\n'
        "  </script>\n"
        "</head>\n"
        "<body>\n"
        f'  <p>Redirecting to <a href="{rel_target}">{rel_target}</a>...</p>\n'
        "</body>\n"
        "</html>\n"
    )


def write_legacy_redirects(site_dir: Path = DEFAULT_SITE_DIR) -> int:
    """Write flat ``.html`` and directory ``/index.html`` redirect stubs for all retired routes."""
    written = 0
    for legacy_route, target_rel in sorted(LEGACY_REDIRECTS.items()):
        flat_rel = f"{legacy_route}.html"
        flat_path = site_dir / flat_rel
        if not flat_path.exists():
            flat_path.parent.mkdir(parents=True, exist_ok=True)
            flat_path.write_text(_render_redirect_html(flat_rel, target_rel), encoding="utf-8")
            written += 1

        if not legacy_route.endswith("/index") and legacy_route != "index":
            dir_rel = f"{legacy_route}/index.html"
        else:
            dir_rel = f"{legacy_route}.html"
        dir_path = site_dir / dir_rel
        if not dir_path.exists():
            dir_path.parent.mkdir(parents=True, exist_ok=True)
            dir_path.write_text(_render_redirect_html(dir_rel, target_rel), encoding="utf-8")
            written += 1
    return written


def run_postbuild(site_dir: Path = DEFAULT_SITE_DIR, docs_dir: Path = DEFAULT_DOCS_DIR) -> None:
    """Execute the full post-build artifact and redirect pipeline."""
    site_dir.mkdir(parents=True, exist_ok=True)
    compact_site_html(site_dir=site_dir)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    build_objects_inv(site_dir=site_dir, docs_dir=docs_dir)
    build_llms_files(site_dir=site_dir, docs_dir=docs_dir)
    write_legacy_redirects(site_dir=site_dir)


def main(argv: list[str] | None = None) -> int:
    """Run ``postbuild.py`` from the CLI."""
    _ = argv
    run_postbuild()
    sys.stdout.write("Postbuild completed: objects.inv, llms.txt, llms-full.txt, .nojekyll, and legacy redirects.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
