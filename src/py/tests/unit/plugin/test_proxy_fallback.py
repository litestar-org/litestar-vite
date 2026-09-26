"""Regression coverage for dev proxy fallback to built static assets."""

from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

from litestar import Litestar
from litestar.testing import TestClient
from litestar.types import Send

from litestar_vite.config import ExternalDevServer, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.plugin import VitePlugin


def _build_vite_app(
    tmp_path: Path,
    *,
    mode: Literal["template", "external", "framework"] = "template",
    runtime: RuntimeConfig | None = None,
) -> Litestar:
    bundle = tmp_path / "dist"
    return Litestar(
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode=mode,
                    paths=PathConfig(
                        root=tmp_path, resource_dir=Path("resources"), bundle_dir=bundle, asset_url="/static/dist/"
                    ),
                    runtime=runtime or RuntimeConfig(dev_mode=True, executor="node"),
                )
            )
        ]
    )


def test_proxy_falls_through_when_hot_file_missing(tmp_path: Path) -> None:
    """Built assets should be served when dev mode is on but Vite is not running."""
    bundle = tmp_path / "dist"
    (bundle / "assets").mkdir(parents=True)
    (bundle / "assets" / "main.js").write_text("console.log('built')")

    app = _build_vite_app(tmp_path)

    with TestClient(app=app) as client:
        response = client.get("/static/dist/assets/main.js")

    assert response.status_code == 200
    assert response.text == "console.log('built')"


def test_proxy_falls_through_for_public_assets(tmp_path: Path) -> None:
    """Built public assets at the bundle root should be served without a hot file."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "logo.svg").write_text("<svg/>")

    app = _build_vite_app(tmp_path)

    with TestClient(app=app) as client:
        response = client.get("/static/dist/logo.svg")

    assert response.status_code == 200
    assert response.text == "<svg/>"


def test_proxy_returns_404_for_missing_asset_when_hot_file_missing(tmp_path: Path) -> None:
    """Missing assets should fall through to static routing and 404, not 503."""
    bundle = tmp_path / "dist"
    bundle.mkdir()

    app = _build_vite_app(tmp_path)

    with TestClient(app=app) as client:
        response = client.get("/static/dist/assets/does-not-exist.js")

    assert response.status_code == 404
    assert response.text != "Vite server not running"


def test_proxy_still_wins_when_hot_file_is_present(tmp_path: Path) -> None:
    """When Vite is running, the proxy response wins over the built static file."""
    bundle = tmp_path / "dist"
    (bundle / "assets").mkdir(parents=True)
    (bundle / "assets" / "main.js").write_text("console.log('built')")
    (bundle / "hot").write_text("http://upstream")
    proxy_calls: list[str] = []

    async def fake_proxy(url: str, *, send: Send, **_kwargs: Any) -> None:
        proxy_calls.append(url)
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/javascript")]})
        await send({"type": "http.response.body", "body": b"upstream", "more_body": False})

    with patch("litestar_vite.plugin._proxy._anyio_proxy_http_request", side_effect=fake_proxy):
        app = _build_vite_app(tmp_path)
        with TestClient(app=app) as client:
            response = client.get("/static/dist/assets/main.js")

    assert response.status_code == 200
    assert response.text == "upstream"
    assert proxy_calls == ["http://upstream/static/dist/assets/main.js"]


def test_external_mode_dev_without_hot_file_still_skips_static_router(tmp_path: Path) -> None:
    """External dev mode should keep its existing no-static-router behavior."""
    bundle = tmp_path / "dist"
    (bundle / "assets").mkdir(parents=True)
    (bundle / "assets" / "main.js").write_text("console.log('built')")

    runtime = RuntimeConfig(
        dev_mode=True,
        executor="node",
        external_dev_server=ExternalDevServer(target="http://localhost:4200"),
    )
    app = _build_vite_app(tmp_path, mode="framework", runtime=runtime)

    with TestClient(app=app) as client:
        response = client.get("/static/dist/assets/main.js")

    assert response.status_code != 200
    assert response.text != "console.log('built')"
