import builtins
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import click
import pytest
from litestar import Litestar, get
from litestar.config.csrf import CSRFConfig
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
    try:
        assert utils._check_h2_available() is False
    finally:
        # Reset the module-level cache so subsequent tests don't observe the
        # monkeypatched outcome (would otherwise leak into integration tests
        # that try to construct a real HTTP/2 client when h2 is missing).
        utils._h2_available = None


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
    try:
        assert utils._check_h2_available() is True
    finally:
        utils._h2_available = None


def test_infer_port_from_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "run", "--port", "5050"])
    assert utils.infer_port_from_argv() == "5050"

    monkeypatch.setattr(sys, "argv", ["litestar", "run", "--port=7070"])
    assert utils.infer_port_from_argv() == "7070"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["litestar", "run", "--host", "0.0.0.0"], "0.0.0.0"),
        (["litestar", "run", "-H", "::1"], "::1"),
        (["litestar", "run", "--host=127.0.0.2"], "127.0.0.2"),
    ],
)
def test_infer_host_from_argv(monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: str) -> None:
    monkeypatch.setattr(sys, "argv", argv)

    assert utils.infer_host_from_argv() == expected


def test_set_environment_uses_effective_litestar_run_bind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The active run command supplies the backend bind before sidecars start."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    context = SimpleNamespace(
        command=SimpleNamespace(name="run"), info_name="run", params={"host": "0.0.0.0", "port": 9123}
    )
    monkeypatch.setattr(click, "get_current_context", lambda *, silent: context)
    monkeypatch.setenv("LITESTAR_HOST", "127.0.0.2")
    monkeypatch.setenv("LITESTAR_PORT", "8123")
    monkeypatch.delenv("APP_URL", raising=False)

    utils.set_environment(config)

    bridge = decode_json((tmp_path / ".litestar.json").read_bytes())
    assert os.environ["LITESTAR_HOST"] == "0.0.0.0"
    assert os.environ["LITESTAR_PORT"] == "9123"
    assert os.environ["APP_URL"] == "http://localhost:9123"
    assert bridge["appUrl"] == "http://localhost:9123"
    assert bridge["litestarPort"] == 9123


def test_set_environment_threads_csrf_config_into_bridge(tmp_path: Path) -> None:
    """set_environment must derive csrfCookieName/csrfHeaderName from app.csrf_config."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    app = Litestar(csrf_config=CSRFConfig(secret="s", cookie_name="custom_cookie", header_name="x-custom-header"))

    utils.set_environment(config, app=app)

    bridge = decode_json((tmp_path / ".litestar.json").read_bytes())
    assert bridge["csrfCookieName"] == "custom_cookie"
    assert bridge["csrfHeaderName"] == "x-custom-header"


def test_set_environment_csrf_names_null_without_app(tmp_path: Path) -> None:
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))

    utils.set_environment(config)

    bridge = decode_json((tmp_path / ".litestar.json").read_bytes())
    assert bridge["csrfCookieName"] is None
    assert bridge["csrfHeaderName"] is None


def test_is_non_serving_assets_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "build"])
    assert utils.is_non_serving_assets_cli() is True

    monkeypatch.setattr(sys, "argv", ["litestar", "run"])
    assert utils.is_non_serving_assets_cli() is False


# ===== is_non_serving_context centralization =====


def test_is_non_serving_context_true_for_assets_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "build"])

    assert utils.is_non_serving_context() is True


def test_is_non_serving_context_false_for_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "run"])

    assert utils.is_non_serving_context() is False


def test_is_non_serving_assets_cli_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["litestar", "assets", "deploy"])

    assert utils.is_non_serving_assets_cli() is True


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
    monkeypatch.setenv("LITESTAR_HOST", "0.0.0.0")
    monkeypatch.setenv("LITESTAR_PORT", "8000")
    monkeypatch.delenv("APP_URL", raising=False)

    utils.set_environment(config, asset_url_override="https://cdn.example.com/")

    assert os.environ["ASSET_URL"] == "https://cdn.example.com/"
    assert os.environ["APP_URL"] == "http://localhost:8000"
    assert os.environ["VITE_HOST"] == "0.0.0.0"
    assert os.environ["VITE_PORT"] == "9999"
    assert os.environ["LITESTAR_VITE_CONFIG_PATH"].endswith(".litestar.json")


def test_log_helpers_tty_normal_uses_rich(monkeypatch: pytest.MonkeyPatch) -> None:
    printer = Mock()
    monkeypatch.setattr(utils, "console", SimpleNamespace(is_terminal=True, print=printer))
    utils.log_warn("warn_msg", level="normal")
    utils.log_fail("fail_msg")
    assert printer.call_count == 2


def test_log_helpers_tty_quiet_suppresses_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    printer = Mock()
    monkeypatch.setattr(utils, "console", SimpleNamespace(is_terminal=True, print=printer))
    utils.log_warn("warn_msg", level="quiet")
    utils.log_fail("fail_msg")
    assert printer.call_count == 1


def test_log_helpers_non_tty_uses_logging(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    printer = Mock()
    monkeypatch.setattr(utils, "console", SimpleNamespace(is_terminal=False, print=printer))
    with caplog.at_level("WARNING", logger="litestar_vite"):
        utils.log_warn("warn_msg", level="normal")
        utils.log_fail("fail_msg")
    assert printer.call_count == 0
    assert "warn_msg" in caplog.text
    assert "fail_msg" in caplog.text


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
