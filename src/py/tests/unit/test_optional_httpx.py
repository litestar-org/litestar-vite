"""Tests validating litestar-vite has zero runtime httpx dependencies."""

import sys
from pathlib import Path

import pytest

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite import typing as typing_facade


def test_typing_facade_excludes_httpx() -> None:
    """Validate typing facade does not expose HTTPX_INSTALLED or ensure_httpx."""
    assert not hasattr(typing_facade, "HTTPX_INSTALLED")
    assert not hasattr(typing_facade, "ensure_httpx")


def test_core_plugin_import_without_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate litestar_vite operates cleanly when httpx is blocked in sys.modules."""
    monkeypatch.setitem(sys.modules, "httpx", None)

    config = ViteConfig(dev_mode=False)
    plugin = VitePlugin(config=config)
    assert plugin.config.dev_mode is False
    assert not hasattr(plugin, "proxy_client")


def test_pyproject_excludes_runtime_httpx() -> None:
    """Validate pyproject.toml does not include httpx in runtime or optional dependencies."""
    pyproject_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    deps_section = content.split("[dependency-groups]")[0]
    assert "httpx" not in deps_section
