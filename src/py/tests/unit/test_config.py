from pathlib import Path, PosixPath

import pytest

from litestar_vite.config import (
    PathConfig,
    RuntimeConfig,
    ViteConfig,
)
from litestar_vite.executor import (
    BunExecutor,
    NodeenvExecutor,
    NodeExecutor,
)


def test_default_vite_config() -> None:
    config = ViteConfig()
    assert isinstance(config.bundle_dir, Path)
    assert isinstance(config.public_dir, Path)
    assert config.ssr_output_dir is None
    assert isinstance(config.resource_dir, Path)
    assert isinstance(config.root_dir, (Path, PosixPath))
    # Default root is current working directory
    assert config.root_dir == Path.cwd()


def test_default_executor_node() -> None:
    config = ViteConfig()
    assert isinstance(config.executor, NodeExecutor)


def test_opt_in_nodeenv_executor() -> None:
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=True))
    assert isinstance(config.executor, NodeenvExecutor)


def test_config_health_check_defaults() -> None:
    config = ViteConfig()
    assert config.health_check is False
    assert config.base_url is None


def test_config_custom_health_check() -> None:
    config = ViteConfig(
        runtime=RuntimeConfig(health_check=True),
        base_url="https://cdn.example.com/",
    )
    assert config.health_check is True
    assert config.base_url == "https://cdn.example.com/"


def test_new_config_structure() -> None:
    """Test the new nested config structure."""
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(
            bundle_dir=Path("/app/dist"),
            resource_dir=Path("/app/src"),
        ),
        runtime=RuntimeConfig(
            dev_mode=True,
            hot_reload=True,
            executor="bun",
        ),
        types=True,  # Shorthand for TypeGenConfig(enabled=True)
    )
    assert config.mode == "spa"
    assert config.bundle_dir == Path("/app/dist")
    assert config.resource_dir == Path("/app/src")
    assert config.is_dev_mode is True
    assert config.hot_reload is True
    assert config.types.enabled is True  # type: ignore
    assert isinstance(config.executor, BunExecutor)


def test_dev_mode_shortcut() -> None:
    """Test the dev_mode shortcut on root config."""
    config = ViteConfig(dev_mode=True)
    assert config.runtime.dev_mode is True
    assert config.is_dev_mode is True


def test_mode_auto_detection_spa_with_index_html(tmp_path: Path) -> None:
    """Test mode auto-detection when index.html exists."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    config = ViteConfig(paths=PathConfig(resource_dir=resource_dir))

    assert config.mode == "spa"
    assert config._mode_auto_detected is True


def test_proxy_mode_defaults_to_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)

    config = RuntimeConfig()

    assert config.proxy_mode == "proxy"


def test_proxy_mode_respects_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITE_PROXY_MODE", "direct")

    config = RuntimeConfig()

    assert config.proxy_mode == "direct"


def test_mode_auto_detection_template_with_jinja(tmp_path: Path) -> None:
    """Test mode auto-detection defaults to template when Jinja2 installed."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    # No index.html

    config = ViteConfig(paths=PathConfig(resource_dir=resource_dir))

    # Should default to template if Jinja2 is available, otherwise spa
    from litestar_vite.config import JINJA_INSTALLED

    if JINJA_INSTALLED:
        assert config.mode == "template"
    else:
        assert config.mode == "spa"
    assert config._mode_auto_detected is True


def test_mode_explicit_overrides_detection(tmp_path: Path) -> None:
    """Test explicit mode overrides auto-detection."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    # Explicitly set to template even though index.html exists
    config = ViteConfig(mode="template", paths=PathConfig(resource_dir=resource_dir))

    assert config.mode == "template"
    assert config._mode_auto_detected is False


def test_validate_mode_spa_missing_index_html(tmp_path: Path) -> None:
    """Test validation fails for SPA mode without index.html in production."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=resource_dir),
        dev_mode=False,
    )

    with pytest.raises(ValueError, match=r"SPA mode requires index\.html"):
        config.validate_mode()


def test_validate_mode_spa_dev_mode_allows_missing_index(tmp_path: Path) -> None:
    """Test validation passes for SPA mode in dev mode even without index.html."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()

    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=resource_dir),
        dev_mode=True,
    )

    # Should not raise
    config.validate_mode()


def test_validate_mode_template_requires_jinja(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validation fails for template mode without Jinja2."""
    # Temporarily disable Jinja2
    import litestar_vite.config

    monkeypatch.setattr(litestar_vite.config, "JINJA_INSTALLED", False)

    config = ViteConfig(mode="template")

    with pytest.raises(ValueError, match="requires Jinja2"):
        config.validate_mode()


def test_mode_detection_prefers_index_html_over_jinja(tmp_path: Path) -> None:
    """Test that index.html presence takes priority in mode detection."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    config = ViteConfig(paths=PathConfig(resource_dir=resource_dir))

    # Even if Jinja2 is installed, should prefer SPA mode due to index.html
    assert config.mode == "spa"
