"""Tests validating litestar-vite behavior when httpx is optional or omitted."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    import pytest


def test_ensure_httpx_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate ensure_httpx raises an ImproperlyConfiguredException when httpx is unavailable."""
    import litestar_vite._typing as typing_module

    monkeypatch.setattr(typing_module, "HTTPX_INSTALLED", False)
    with pytest.raises(ImproperlyConfiguredException, match="requires 'httpx' to be installed"):
        typing_module.ensure_httpx("HTTP proxy")


def test_ensure_httpx_passes_when_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate ensure_httpx executes silently when httpx is marked installed."""
    import litestar_vite._typing as typing_module

    monkeypatch.setattr(typing_module, "HTTPX_INSTALLED", True)
    typing_module.ensure_httpx("HTTP proxy")


def test_core_plugin_import_without_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate litestar_vite modules import cleanly when httpx is not in sys.modules."""
    import litestar_vite._typing as typing_module

    monkeypatch.setattr(typing_module, "HTTPX_INSTALLED", False)
    from litestar_vite import ViteConfig, VitePlugin

    config = ViteConfig(dev_mode=False)
    plugin = VitePlugin(config=config)
    assert plugin.config.dev_mode is False


def test_proxy_client_raises_without_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate proxy_client property raises actionable ImproperlyConfiguredException when httpx is absent."""
    import litestar_vite._typing as typing_module
    from litestar_vite import ViteConfig, VitePlugin

    monkeypatch.setattr(typing_module, "HTTPX_INSTALLED", False)
    plugin = VitePlugin(config=ViteConfig(dev_mode=True))
    with pytest.raises(ImproperlyConfiguredException, match="requires 'httpx' to be installed"):
        _ = plugin.proxy_client
