"""Unit tests for Link preload headers and 103 Early Hints in AppHandler and InertiaResponse."""

from pathlib import Path
from typing import Any

from litestar import Litestar, get
from litestar.testing import create_test_client

from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.inertia import InertiaHeaders
from litestar_vite.plugin import VitePlugin


def _write_production_bundle(bundle_dir: Path) -> None:
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True)
    (bundle_dir / "manifest.json").write_text(
        '{"src/main.ts": {"file": "assets/main-abc12345.js", "src": "src/main.ts", "isEntry": true, "css": ["assets/main-def67890.css"]}}',
        encoding="utf-8",
    )
    (bundle_dir / "index.html").write_text(
        '<!doctype html><html><head><script type="module" src="/src/main.ts"></script></head><body><div id="app"></div></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "main-abc12345.js").write_text("console.log('ok');", encoding="utf-8")
    (assets_dir / "main-def67890.css").write_text("body { margin: 0; }", encoding="utf-8")


def test_app_handler_attaches_link_preload_headers_in_production(tmp_path: Path) -> None:
    """Verify AppHandler attaches RFC 8288 Link preload headers on production HTML responses."""
    bundle_dir = tmp_path / "public"
    _write_production_bundle(bundle_dir)

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, resource_dir=tmp_path, asset_url="/static/"),
        runtime=RuntimeConfig(dev_mode=False, link_preload_headers=True),
    )

    with create_test_client(route_handlers=[], plugins=[VitePlugin(config=config)]) as client:
        response = client.get("/")
        assert response.status_code == 200
        link_header = response.headers.get("link") or ""
        assert "</static/assets/main-abc12345.js>; rel=modulepreload; as=script; crossorigin" in link_header
        assert "</static/assets/main-def67890.css>; rel=preload; as=style" in link_header


def test_inertia_response_attaches_link_preload_headers_on_html_bootstrap_only(tmp_path: Path) -> None:
    """Verify InertiaResponse attaches Link preload headers on HTML responses and not X-Inertia JSON responses."""
    bundle_dir = tmp_path / "public"
    _write_production_bundle(bundle_dir)

    @get("/dashboard", component="Dashboard")
    async def dashboard() -> dict[str, Any]:
        return {"user": "Ada"}

    config = ViteConfig(
        mode="hybrid",
        paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, resource_dir=tmp_path, asset_url="/static/"),
        runtime=RuntimeConfig(dev_mode=False, link_preload_headers=True),
        inertia=InertiaConfig(root_template="index.html"),
    )

    with create_test_client(route_handlers=[dashboard], plugins=[VitePlugin(config=config)]) as client:
        html_resp = client.get("/dashboard")
        assert html_resp.status_code == 200
        link_header = html_resp.headers.get("link") or ""
        assert "</static/assets/main-abc12345.js>; rel=modulepreload; as=script; crossorigin" in link_header
        assert "</static/assets/main-def67890.css>; rel=preload; as=style" in link_header

        json_resp = client.get("/dashboard", headers={InertiaHeaders.ENABLED.value: "true"})
        assert json_resp.status_code == 200
        assert "link" not in json_resp.headers


async def test_early_hints_sent_when_enabled_and_supported_by_scope(tmp_path: Path) -> None:
    """Verify 103 Early Hints (http.response.informational) are sent before 200 OK when early_hints=True."""
    bundle_dir = tmp_path / "public"
    _write_production_bundle(bundle_dir)

    @get("/dashboard", component="Dashboard")
    async def dashboard() -> dict[str, Any]:
        return {"user": "Ada"}

    config = ViteConfig(
        mode="hybrid",
        paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, resource_dir=tmp_path, asset_url="/static/"),
        runtime=RuntimeConfig(dev_mode=False, link_preload_headers=True, early_hints=True),
        inertia=InertiaConfig(root_template="index.html"),
    )
    plugin = VitePlugin(config=config)
    app = Litestar(route_handlers=[dashboard], plugins=[plugin])
    if plugin.spa_handler is not None:
        await plugin.spa_handler.initialize_async()

    sent_messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "2",
        "method": "GET",
        "scheme": "https",
        "path": "/dashboard",
        "raw_path": b"/dashboard",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver.local", 443),
        "state": {},
        "extensions": {"http.response.informational": {}},
    }

    await app(scope, receive, send)  # type: ignore[arg-type]

    informational = [m for m in sent_messages if m.get("type") == "http.response.informational"]
    assert len(informational) == 1
    assert informational[0]["status"] == 103
    early_links = [
        val.decode("latin-1") for key, val in informational[0].get("headers", []) if key.lower() == b"link"
    ]
    assert "</static/assets/main-abc12345.js>; rel=modulepreload; as=script; crossorigin" in early_links
    assert "</static/assets/main-def67890.css>; rel=preload; as=style" in early_links

    start_idx = next(i for i, m in enumerate(sent_messages) if m.get("type") == "http.response.start")
    info_idx = next(i for i, m in enumerate(sent_messages) if m.get("type") == "http.response.informational")
    assert info_idx < start_idx
