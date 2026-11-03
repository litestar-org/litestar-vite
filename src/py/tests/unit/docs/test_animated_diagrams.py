"""Unit tests for the 6 animated SVG/CSS architecture diagrams and docs/architecture/*.md pages."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]

EXPECTED_DIAGRAMS: dict[str, tuple[str, ...]] = {
    "diagram-dev-proxy.html": ("ViteProxyMiddleware", "anyio.connect_tcp", "/vite-hmr", ".litestar.json"),
    "diagram-dev-vs-prod.html": ("Development Mode", "Production Mode", "manifest.json", "Immutable caching + metadata blocking"),
    "diagram-operating-modes.html": (
        "lv-mode-spa",
        "lv-mode-hybrid",
        "lv-mode-template",
        "lv-mode-framework",
        "litestar-island",
    ),
    "diagram-inertia-lifecycle.html": ("X-Inertia", "X-Inertia-Partial-Data", "defer()", "PageProps"),
    "diagram-ssr-ipc.html": ("TCPStreamIPCTransport", "/__litestar_ssr__", "StdioIPCTransport", "SSRCircuitBreaker"),
    "diagram-typegen-pipeline.html": (
        "openapi.json",
        "asyncapi.json",
        "routes.json",
        "@hey-api/openapi-ts",
        "createTypedChannels",
    ),
}

EXPECTED_ARCHITECTURE_PAGES: dict[str, tuple[str, ...]] = {
    "docs/architecture/index.md": (
        '--8<-- "tools/docs/includes/diagram-operating-modes.html"',
        '--8<-- "tools/docs/includes/diagram-dev-vs-prod.html"',
    ),
    "docs/architecture/dev-proxy-and-bridge.md": (
        '--8<-- "tools/docs/includes/diagram-dev-proxy.html"',
        "ViteProxyMiddleware",
        ".litestar.json",
    ),
    "docs/architecture/ssr-and-ipc.md": (
        '--8<-- "tools/docs/includes/diagram-ssr-ipc.html"',
        '--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"',
        "TCPStreamIPCTransport",
        "StdioIPCTransport",
    ),
    "docs/architecture/codegen-pipeline.md": (
        '--8<-- "tools/docs/includes/diagram-typegen-pipeline.html"',
        "openapi.json",
        "asyncapi.json",
        "routes.json",
    ),
}


def test_all_six_animated_diagrams_exist_and_satisfy_svg_a11y_and_motion_contracts() -> None:
    """Verify all 6 diagram fragments include accessible SVG tags, CSS variables, and reduced-motion rules."""
    includes_dir = REPO_ROOT / "tools" / "docs" / "includes"
    for filename, required_tokens in EXPECTED_DIAGRAMS.items():
        path = includes_dir / filename
        assert path.exists(), f"Missing diagram fragment: {path}"
        text = path.read_text(encoding="utf-8")
        assert "<svg" in text, f"Missing <svg> in {filename}"
        assert 'role="img"' in text, f"Missing role='img' in {filename}"
        assert "<title" in text, f"Missing <title> in {filename}"
        assert "<desc" in text, f"Missing <desc> in {filename}"
        assert "@keyframes" in text, f"Missing @keyframes animation in {filename}"
        assert "prefers-reduced-motion: reduce" in text, f"Missing reduced-motion media query in {filename}"
        assert "--md-" in text, f"Missing theme CSS variables in {filename}"
        for token in required_tokens:
            assert token in text, f"Missing expected token {token!r} in {filename}"


def test_operating_modes_diagram_provides_interactive_css_tabs() -> None:
    """Verify diagram-operating-modes.html includes pure-CSS radio inputs for all 4 operating modes."""
    path = REPO_ROOT / "tools" / "docs" / "includes" / "diagram-operating-modes.html"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert 'type="radio"' in text
    for mode_id in ("lv-mode-spa", "lv-mode-hybrid", "lv-mode-template", "lv-mode-framework"):
        assert f'id="{mode_id}"' in text
        assert f'for="{mode_id}"' in text


def test_architecture_pages_exist_and_embed_animated_diagrams() -> None:
    """Verify all 4 docs/architecture/*.md pages exist and embed the animated diagrams via --8<--."""
    for rel_path, required_snippets in EXPECTED_ARCHITECTURE_PAGES.items():
        page_path = REPO_ROOT / rel_path
        assert page_path.exists(), f"Missing architecture page: {rel_path}"
        text = page_path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            assert snippet in text, f"Missing {snippet!r} in {rel_path}"
