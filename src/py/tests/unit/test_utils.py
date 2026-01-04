import builtins
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from litestar import Litestar, get
from litestar.connection import Request
from litestar.serialization import decode_json

from litestar_vite.config import DeployConfig, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig
from litestar_vite.plugin import _utils as utils


def test_is_proxy_debug_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITE_PROXY_DEBUG", "true")
    utils._vite_proxy_debug = None
    assert utils.is_proxy_debug() is True

    monkeypatch.setenv("VITE_PROXY_DEBUG", "false")
    assert utils.is_proxy_debug() is True

    utils._vite_proxy_debug = None


def test_check_h2_available_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    utils._h2_available = None
    orig_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> object:
        if name == "h2":
            raise ImportError
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert utils._check_h2_available() is False


def test_check_h2_available_success(monkeypatch: pytest.MonkeyPatch) -> None:
    utils._h2_available = None
    orig_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> object:
        if name == "h2":
            return SimpleNamespace()
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert utils._check_h2_available() is True


def test_infer_port_from_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "run", "--port", "5050"])
    assert utils.infer_port_from_argv() == "5050"

    monkeypatch.setattr(sys, "argv", ["litestar", "run", "--port=7070"])
    assert utils.infer_port_from_argv() == "7070"


def test_is_non_serving_assets_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "build"])
    assert utils.is_non_serving_assets_cli() is True

    monkeypatch.setattr(sys, "argv", ["litestar", "run"])
    assert utils.is_non_serving_assets_cli() is False


def test_write_runtime_config_file_records_deploy_asset_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_VERSION", "9.9.9")
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, resource_dir="src", bundle_dir="public", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=False),
        types=TypeGenConfig(output=Path("src/generated")),
        deploy=DeployConfig(enabled=True, storage_backend="s3://bucket", asset_url="https://cdn.example.com/"),
    )

    path_str, changed = utils.write_runtime_config_file(config, return_status=True)
    data = decode_json(Path(path_str).read_text())

    assert changed is True
    assert data["deployAssetUrl"] == "https://cdn.example.com/"
    assert data["types"]["routesTsPath"].endswith("src/generated/routes.ts")
    assert data["types"]["schemasTsPath"].endswith("src/generated/schemas.ts")


def test_set_environment_sets_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(root=tmp_path, resource_dir="src", bundle_dir="public", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=True, host="0.0.0.0", port=9999),
    )

    monkeypatch.delenv("ASSET_URL", raising=False)
    monkeypatch.delenv("VITE_HOST", raising=False)
    monkeypatch.delenv("VITE_PORT", raising=False)
    monkeypatch.delenv("LITESTAR_HOST", raising=False)
    monkeypatch.delenv("LITESTAR_PORT", raising=False)

    utils.set_environment(config, asset_url_override="https://cdn.example.com/")

    assert os.environ["ASSET_URL"] == "https://cdn.example.com/"
    assert os.environ["VITE_HOST"] == "0.0.0.0"
    assert os.environ["VITE_PORT"] == "9999"
    assert os.environ["LITESTAR_VITE_CONFIG_PATH"].endswith(".litestar.json")


def test_log_helpers_print(monkeypatch: pytest.MonkeyPatch) -> None:
    printer = Mock()
    monkeypatch.setattr(utils, "console", SimpleNamespace(print=printer))

    utils.log_success("ok")
    utils.log_info("info")
    utils.log_warn("warn")
    utils.log_fail("fail")

    assert printer.call_count == 4


def test_route_prefix_cache_and_inertia_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    @get("/api/items")
    async def handler() -> dict[str, str]:
        return {"ok": "yes"}

    app = Litestar(route_handlers=[handler])

    monkeypatch.setenv("VITE_PROXY_DEBUG", "true")
    utils._vite_proxy_debug = None

    prefixes = utils.get_litestar_route_prefixes(app)
    assert "/api/items" in prefixes

    assert utils.is_litestar_route("/api/items", app) is True

    sentinel = Mock()
    monkeypatch.setattr("litestar_vite.inertia.exception_handler.exception_to_http_response", lambda *_: sentinel)

    request = cast("Request[Any, Any, Any]", SimpleNamespace(headers={"x-inertia": "true"}))
    response = utils.vite_not_found_handler(request, Mock())
    assert response is sentinel

    request = cast("Request[Any, Any, Any]", SimpleNamespace(headers={}))
    response = utils.vite_not_found_handler(request, Mock())
    assert response.status_code == 404
