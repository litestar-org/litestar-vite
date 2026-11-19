"""Tests for ``litestar_vite.utils.read_bridge_config`` (litestar-vite-c1t.1).

The bridge config (``.litestar.json``) is the source of truth for browser-facing
bridge fields such as ``appUrl``. This helper resolves and parses that file with
mtime-based caching.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from litestar.serialization import decode_json

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.plugin import _utils as plugin_utils
from litestar_vite.utils import read_bridge_config

# ===== Fixtures and helpers =====


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Reset the per-process cache between tests to keep cases independent."""
    read_bridge_config.cache_clear()


def _write_bridge(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload))
    return path


# ===== File-presence and shape =====


def test_read_bridge_config_returns_dict_when_file_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _write_bridge(
        tmp_path / ".litestar.json", {"appUrl": "http://localhost:8000", "host": "127.0.0.1", "port": 5173}
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    result = read_bridge_config()

    assert isinstance(result, dict)
    assert result["appUrl"] == "http://localhost:8000"
    assert result["host"] == "127.0.0.1"
    assert result["port"] == 5173


def test_read_bridge_config_returns_none_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "does-not-exist.json"))

    assert read_bridge_config() is None


def test_read_bridge_config_returns_none_when_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = tmp_path / ".litestar.json"
    bridge.write_text("not json{")
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    assert read_bridge_config() is None


def test_read_bridge_config_returns_none_when_not_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _write_bridge(tmp_path / ".litestar.json", [1, 2, 3])
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    assert read_bridge_config() is None


# ===== Path resolution order =====


def test_read_bridge_config_resolution_explicit_arg_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_a = _write_bridge(tmp_path / "a.json", {"appUrl": "http://a", "host": "a", "port": 1})
    file_b = _write_bridge(tmp_path / "b.json", {"appUrl": "http://b", "host": "b", "port": 2})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(file_a))

    result = read_bridge_config(file_b)

    assert result is not None
    assert result["appUrl"] == "http://b"


def test_read_bridge_config_resolution_env_var_then_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITESTAR_VITE_CONFIG_PATH", raising=False)
    _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://cwd", "host": "h", "port": 3})
    monkeypatch.chdir(tmp_path)

    result = read_bridge_config()

    assert result is not None
    assert result["appUrl"] == "http://cwd"


# ===== Caching behavior =====


def test_read_bridge_config_cache_hit_skips_file_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cache hit must avoid re-parsing JSON (NFR2).

    The mtime-revalidation strategy (DP1 option (a)) still performs a single
    ``Path.stat()`` per call to detect changes — but no read or decode should
    occur when the mtime is unchanged.
    """
    import litestar_vite.utils as utils

    bridge = _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://cached", "host": "h", "port": 4})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    decode_count = 0
    real_decode = utils.decode_json

    def counting_decode(value: str | bytes) -> object:
        nonlocal decode_count
        decode_count += 1
        return real_decode(value)

    monkeypatch.setattr(utils, "decode_json", counting_decode)

    first = read_bridge_config()
    second = read_bridge_config()

    assert first == second
    assert second is not None
    assert second["appUrl"] == "http://cached"
    assert decode_count == 1


def test_read_bridge_config_cache_invalidated_on_mtime_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://before", "host": "h", "port": 5})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    first = read_bridge_config()
    assert first is not None
    assert first["appUrl"] == "http://before"

    _write_bridge(bridge, {"appUrl": "http://after", "host": "h", "port": 5})
    # Ensure mtime advances even on coarse-resolution filesystems.
    future = time.time() + 5
    os.utime(bridge, (future, future))

    second = read_bridge_config()

    assert second is not None
    assert second["appUrl"] == "http://after"


def test_read_bridge_config_cache_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://one", "host": "h", "port": 6})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    first = read_bridge_config()
    assert first is not None
    assert first["appUrl"] == "http://one"

    _write_bridge(bridge, {"appUrl": "http://two", "host": "h", "port": 6})
    read_bridge_config.cache_clear()
    # Force mtime backwards so only cache_clear (not mtime detection) accounts for the re-read.
    os.utime(bridge, (0, 0))

    second = read_bridge_config()
    assert second is not None
    assert second["appUrl"] == "http://two"


@pytest.mark.parametrize(("initial_value", "expected_value"), [(None, None), ("1", "1"), ("false", "false")])
def test_set_environment_preserves_loopback_default_for_vite_allow_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initial_value: str | None, expected_value: str | None
) -> None:
    """Verify set_environment leaves VITE_ALLOW_REMOTE unset unless explicitly provided."""
    if initial_value is None:
        monkeypatch.delenv("VITE_ALLOW_REMOTE", raising=False)
    else:
        monkeypatch.setenv("VITE_ALLOW_REMOTE", initial_value)

    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    plugin_utils.set_environment(config)

    assert os.environ.get("VITE_ALLOW_REMOTE") == expected_value


def test_write_runtime_config_file_emits_proxy_token_and_enforces_0600_mode(tmp_path: Path) -> None:
    """Verify atomic bridge writes emit a stable per-process proxyToken with 0o600 permissions."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))

    path_str, first_changed = plugin_utils.write_runtime_config_file(config, return_status=True)
    bridge_path = Path(path_str)
    first_data = decode_json(bridge_path.read_bytes())

    assert first_changed is True
    assert isinstance(first_data["proxyToken"], str)
    assert len(first_data["proxyToken"]) >= 32
    assert bridge_path.read_bytes().endswith(b"\n")
    assert list(tmp_path.glob("*.tmp")) == []
    if os.name == "posix":
        assert (bridge_path.stat().st_mode & 0o777) == 0o600

    _, second_changed = plugin_utils.write_runtime_config_file(config, return_status=True)
    second_data = decode_json(bridge_path.read_bytes())

    assert second_changed is False
    assert second_data["proxyToken"] == first_data["proxyToken"]

    if os.name == "posix":
        bridge_path.chmod(0o644)
        assert (bridge_path.stat().st_mode & 0o777) == 0o644

        _, third_changed = plugin_utils.write_runtime_config_file(config, return_status=True)

        assert third_changed is False
        assert (bridge_path.stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize("stored_token", ["test-token-placeholder", None])
def test_write_runtime_config_file_outside_dev_mode_is_unchanged_across_processes(
    tmp_path: Path, stored_token: str | None
) -> None:
    """Verify non-dev bridge writes keep the stored token and skip rewriting an unchanged file."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False))

    path_str, first_changed = plugin_utils.write_runtime_config_file(
        config, proxy_token=stored_token, return_status=True
    )
    bridge_path = Path(path_str)
    first_bytes = bridge_path.read_bytes()

    assert first_changed is True
    assert decode_json(first_bytes)["proxyToken"] == stored_token

    plugin_utils._get_or_create_bridge_proxy_token.cache_clear()
    _, second_changed = plugin_utils.write_runtime_config_file(config, return_status=True)

    assert second_changed is False
    assert bridge_path.read_bytes() == first_bytes


def test_write_runtime_config_file_in_dev_mode_issues_new_token_per_process(tmp_path: Path) -> None:
    """Verify a new development process replaces the stored token with its own."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))

    path_str = plugin_utils.write_runtime_config_file(config)
    first_token = decode_json(Path(path_str).read_bytes())["proxyToken"]

    plugin_utils._get_or_create_bridge_proxy_token.cache_clear()
    _, changed = plugin_utils.write_runtime_config_file(config, return_status=True)
    second_token = decode_json(Path(path_str).read_bytes())["proxyToken"]

    assert changed is True
    assert isinstance(second_token, str)
    assert second_token != first_token


def test_write_runtime_config_file_explicit_proxy_token_invalidates_bridge_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify explicit proxy_token overrides the generated token and invalidates the bridge cache."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    first_path = Path(plugin_utils.write_runtime_config_file(config, proxy_token="test-token-placeholder"))
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(first_path))

    assert plugin_utils.get_bridge_proxy_token() == "test-token-placeholder"

    updated_path, changed = plugin_utils.write_runtime_config_file(
        config, proxy_token="test-token-placeholder-updated", return_status=True
    )

    assert changed is True
    assert Path(updated_path) == first_path
    assert plugin_utils.get_bridge_proxy_token() == "test-token-placeholder-updated"


def test_write_runtime_config_file_cleans_temp_file_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify failed atomic replacement unlinks the temporary file before propagating."""
    config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=True))

    def fail_replace(self: Path, target: Path) -> Path:
        msg = "simulated replace failure"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        plugin_utils.write_runtime_config_file(config)

    assert list(tmp_path.glob("*.tmp")) == []


def test_get_bridge_proxy_token_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_bridge_proxy_token follows explicit path, env var, and missing-file semantics."""
    env_config = ViteConfig(mode="spa", paths=PathConfig(root=tmp_path / "env"), runtime=RuntimeConfig(dev_mode=True))
    explicit_config = ViteConfig(
        mode="spa", paths=PathConfig(root=tmp_path / "explicit"), runtime=RuntimeConfig(dev_mode=True)
    )
    env_path = Path(plugin_utils.write_runtime_config_file(env_config, proxy_token="test-token-placeholder-env"))
    explicit_path = Path(
        plugin_utils.write_runtime_config_file(explicit_config, proxy_token="test-token-placeholder-explicit")
    )

    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(env_path))
    assert plugin_utils.get_bridge_proxy_token() == "test-token-placeholder-env"
    assert plugin_utils.get_bridge_proxy_token(explicit_path) == "test-token-placeholder-explicit"

    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))
    assert plugin_utils.get_bridge_proxy_token() is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"proxyToken": "test-token-placeholder"}, "test-token-placeholder"),
        ({"appUrl": "http://localhost:8000"}, None),
        ({"proxyToken": None}, None),
        ({"proxyToken": ""}, None),
        ({"proxyToken": 123}, None),
    ],
)
def test_get_bridge_proxy_token_payload_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict[str, object], expected: str | None
) -> None:
    """Verify get_bridge_proxy_token returns only non-empty string tokens."""
    bridge = _write_bridge(tmp_path / ".litestar.json", payload)
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    assert plugin_utils.get_bridge_proxy_token() == expected
