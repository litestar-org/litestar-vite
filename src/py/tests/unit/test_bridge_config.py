"""Tests for ``litestar_vite.utils.read_bridge_config`` (litestar-vite-c1t.1).

The bridge config (``.litestar.json``) is the single source of truth for URL
fields consumed by both the loader and the Vite-mode proxy middleware. This
helper resolves and parses that file with mtime-based caching.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

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


def test_read_bridge_config_returns_dict_when_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = _write_bridge(
        tmp_path / ".litestar.json",
        {"appUrl": "http://localhost:8000", "host": "127.0.0.1", "port": 5173},
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    result = read_bridge_config()

    assert isinstance(result, dict)
    assert result["appUrl"] == "http://localhost:8000"
    assert result["host"] == "127.0.0.1"
    assert result["port"] == 5173


def test_read_bridge_config_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "does-not-exist.json"))

    assert read_bridge_config() is None


def test_read_bridge_config_returns_none_when_malformed_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = tmp_path / ".litestar.json"
    bridge.write_text("not json{")
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    assert read_bridge_config() is None


def test_read_bridge_config_returns_none_when_not_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = _write_bridge(tmp_path / ".litestar.json", [1, 2, 3])
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    assert read_bridge_config() is None


# ===== Path resolution order =====


def test_read_bridge_config_resolution_explicit_arg_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_a = _write_bridge(tmp_path / "a.json", {"appUrl": "http://a", "host": "a", "port": 1})
    file_b = _write_bridge(tmp_path / "b.json", {"appUrl": "http://b", "host": "b", "port": 2})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(file_a))

    result = read_bridge_config(file_b)

    assert result is not None
    assert result["appUrl"] == "http://b"


def test_read_bridge_config_resolution_env_var_then_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LITESTAR_VITE_CONFIG_PATH", raising=False)
    _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://cwd", "host": "h", "port": 3})
    monkeypatch.chdir(tmp_path)

    result = read_bridge_config()

    assert result is not None
    assert result["appUrl"] == "http://cwd"


# ===== Caching behavior =====


def test_read_bridge_config_cache_hit_skips_file_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cache hit must avoid re-parsing JSON (NFR2).

    The mtime-revalidation strategy (DP1 option (a)) still performs a single
    ``Path.stat()`` per call to detect changes — but no read or decode should
    occur when the mtime is unchanged.
    """
    import msgspec

    bridge = _write_bridge(tmp_path / ".litestar.json", {"appUrl": "http://cached", "host": "h", "port": 4})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    decode_count = 0
    real_decode = msgspec.json.decode

    def counting_decode(*args: object, **kwargs: object) -> object:
        nonlocal decode_count
        decode_count += 1
        return real_decode(*args, **kwargs)

    monkeypatch.setattr(msgspec.json, "decode", counting_decode)

    first = read_bridge_config()
    second = read_bridge_config()

    assert first == second
    assert second is not None
    assert second["appUrl"] == "http://cached"
    assert decode_count == 1


def test_read_bridge_config_cache_invalidated_on_mtime_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
