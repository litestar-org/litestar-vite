from pathlib import Path, PosixPath

import pytest

from litestar_vite.config import (
    ExternalDevServer,
    PathConfig,
    RuntimeConfig,
    SPAConfig,
    TypeGenConfig,
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


def test_config_health_check_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure env defaults don't leak into config
    monkeypatch.delenv("VITE_BASE_URL", raising=False)
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
            dev_server_mode="vite_proxy",  # Use new field
            executor="bun",
        ),
        types=True,  # Shorthand for TypeGenConfig(enabled=True)
    )
    assert config.mode == "spa"
    assert config.bundle_dir == Path("/app/dist")
    assert config.resource_dir == Path("/app/src")
    assert config.is_dev_mode is True
    assert config.hot_reload is True  # Derived from dev_server_mode
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


def test_dev_server_mode_defaults_to_vite_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test dev_server_mode defaults to vite_proxy."""
    monkeypatch.delenv("VITE_DEV_SERVER_MODE", raising=False)

    config = RuntimeConfig()

    assert config.dev_server_mode == "vite_proxy"


def test_dev_server_mode_respects_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_DEV_SERVER_MODE=direct maps to vite_direct."""
    monkeypatch.setenv("VITE_DEV_SERVER_MODE", "direct")

    config = RuntimeConfig()

    assert config.dev_server_mode == "vite_direct"


def test_dev_server_mode_respects_vite_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_DEV_SERVER_MODE=vite_direct is recognized."""
    monkeypatch.setenv("VITE_DEV_SERVER_MODE", "vite_direct")

    config = RuntimeConfig()

    assert config.dev_server_mode == "vite_direct"


def test_dev_server_mode_respects_external_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_DEV_SERVER_MODE=external_proxy is recognized."""
    monkeypatch.setenv("VITE_DEV_SERVER_MODE", "external_proxy")

    config = RuntimeConfig(external_dev_server="http://localhost:4200")

    assert config.dev_server_mode == "external_proxy"


# ============================================================================
# ExternalDevServer tests
# ============================================================================


def test_external_dev_server_defaults() -> None:
    """Test ExternalDevServer has sensible defaults."""
    ext = ExternalDevServer()

    assert ext.target == "http://localhost:4200"
    assert ext.http2 is False
    assert ext.enabled is True


def test_external_dev_server_custom_values() -> None:
    """Test ExternalDevServer with custom values."""
    ext = ExternalDevServer(
        target="http://localhost:3000",
        http2=True,
        enabled=False,
    )

    assert ext.target == "http://localhost:3000"
    assert ext.http2 is True
    assert ext.enabled is False


def test_runtime_config_external_dev_server_string_normalization() -> None:
    """Test external_dev_server string is normalized to ExternalDevServer."""
    config = RuntimeConfig(
        dev_server_mode="external_proxy",
        external_dev_server="http://localhost:3000",
    )

    assert isinstance(config.external_dev_server, ExternalDevServer)
    assert config.external_dev_server.target == "http://localhost:3000"


def test_runtime_config_external_dev_server_object() -> None:
    """Test external_dev_server can be passed as object."""
    ext = ExternalDevServer(target="http://localhost:4200", http2=True)
    config = RuntimeConfig(
        dev_server_mode="external_proxy",
        external_dev_server=ext,
    )

    assert config.external_dev_server is ext
    assert isinstance(config.external_dev_server, ExternalDevServer)
    assert config.external_dev_server.http2 is True


def test_runtime_config_external_proxy_requires_target() -> None:
    """Test external_proxy mode requires external_dev_server."""
    with pytest.raises(ValueError, match="external_dev_server is required"):
        RuntimeConfig(dev_server_mode="external_proxy", external_dev_server=None)


def test_vite_config_external_proxy_mode() -> None:
    """Test ViteConfig with external_proxy mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True,
            dev_server_mode="external_proxy",
            external_dev_server=ExternalDevServer(target="http://localhost:4200"),
        )
    )

    assert config.dev_server_mode == "external_proxy"
    assert config.external_dev_server is not None
    assert config.external_dev_server.target == "http://localhost:4200"
    # HMR disabled for external servers
    assert config.hot_reload is False


def test_hot_reload_derived_from_vite_proxy_mode() -> None:
    """Test hot_reload is True for vite_proxy mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True,
            dev_server_mode="vite_proxy",
        )
    )

    assert config.hot_reload is True


def test_hot_reload_derived_from_vite_direct_mode() -> None:
    """Test hot_reload is True for vite_direct mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True,
            dev_server_mode="vite_direct",
        )
    )

    assert config.hot_reload is True


def test_hot_reload_disabled_for_external_proxy() -> None:
    """Test hot_reload is False for external_proxy mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True,
            dev_server_mode="external_proxy",
            external_dev_server="http://localhost:4200",
        )
    )

    assert config.hot_reload is False


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


def test_type_paths_resolve_relative_and_cascade(tmp_path: Path) -> None:
    """TypeGen paths resolve under paths.root and cascade when only output is set."""
    root = tmp_path / "js"
    config = ViteConfig(
        paths=PathConfig(root=root),
        types=TypeGenConfig(
            enabled=True,
            output=Path("src/generated/types"),  # only output overridden
        ),
    )

    assert isinstance(config.types, TypeGenConfig)
    assert config.types.output == root / "src/generated/types"
    # openapi/routes cascade under output when not explicitly set
    assert config.types.openapi_path == root / "src/generated/types/openapi.json"
    assert config.types.routes_path == root / "src/generated/types/routes.json"


def test_dev_mode_not_auto_enabled_when_mode_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit mode should skip auto dev-mode even when no built assets."""
    monkeypatch.setenv("VITE_AUTO_DEV_MODE", "True")
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()

    config = ViteConfig(
        mode="spa",  # explicit
        dev_mode=False,
        paths=PathConfig(root=tmp_path, resource_dir=resource_dir, bundle_dir=tmp_path / "public"),
    )

    assert config.runtime.dev_mode is False


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


# ============================================================================
# SPAConfig tests
# ============================================================================


def test_spa_config_defaults() -> None:
    """Test SPAConfig has sensible defaults."""
    spa_config = SPAConfig()

    assert spa_config.inject_routes is True
    assert spa_config.routes_var_name == "__LITESTAR_ROUTES__"
    assert spa_config.routes_include is None
    assert spa_config.routes_exclude == ["vite_spa"]  # Excludes catch-all by default
    assert spa_config.app_selector == "#app"
    assert spa_config.cache_transformed_html is True


def test_spa_config_custom_values() -> None:
    """Test SPAConfig with custom values."""
    spa_config = SPAConfig(
        inject_routes=False,
        routes_var_name="ROUTES",
        routes_include=["api_*", "public_*"],
        routes_exclude=["_internal"],
        app_selector="#root",
        cache_transformed_html=False,
    )

    assert spa_config.inject_routes is False
    assert spa_config.routes_var_name == "ROUTES"
    assert spa_config.routes_include == ["api_*", "public_*"]
    assert spa_config.routes_exclude == ["_internal"]
    assert spa_config.app_selector == "#root"
    assert spa_config.cache_transformed_html is False


def test_vite_config_spa_bool_shortcut() -> None:
    """Test spa=True creates SPAConfig with defaults."""
    config = ViteConfig(spa=True)

    assert isinstance(config.spa, SPAConfig)
    assert config.spa_config is not None
    assert config.spa_config.inject_routes is True
    assert config.spa_config.routes_var_name == "__LITESTAR_ROUTES__"


def test_vite_config_spa_false() -> None:
    """Test spa=False explicitly disables SPA config."""
    config = ViteConfig(mode="spa", spa=False)

    assert config.spa is False
    assert config.spa_config is None


def test_vite_config_spa_explicit_config() -> None:
    """Test spa can be set to an explicit SPAConfig."""
    spa_config = SPAConfig(
        routes_var_name="__CUSTOM_ROUTES__",
        routes_exclude=["_internal*"],
    )
    config = ViteConfig(spa=spa_config)

    assert config.spa is spa_config
    assert config.spa_config is spa_config
    assert config.spa_config.routes_var_name == "__CUSTOM_ROUTES__"
    assert config.spa_config.routes_exclude == ["_internal*"]


def test_vite_config_spa_auto_enabled_for_spa_mode(tmp_path: Path) -> None:
    """Test that SPAConfig is auto-enabled when mode='spa'."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    # Don't explicitly set spa - it should be auto-enabled for mode="spa"
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(resource_dir=resource_dir),
    )

    assert isinstance(config.spa, SPAConfig)
    assert config.spa_config is not None
    assert config.spa_config.inject_routes is True


def test_vite_config_spa_not_auto_enabled_for_template_mode() -> None:
    """Test that SPAConfig is NOT auto-enabled for template mode."""
    config = ViteConfig(mode="template")

    # spa should remain False for template mode
    assert config.spa is False
    assert config.spa_config is None


def test_vite_config_spa_can_be_explicitly_disabled() -> None:
    """Test that spa=False prevents auto-enabling even for SPA mode."""
    config = ViteConfig(mode="spa", spa=False)

    # Explicitly disabled, should stay False
    assert config.spa is False
    assert config.spa_config is None
