from pathlib import Path, PosixPath
from typing import cast

import pytest

from litestar_vite.config import (
    DeployConfig,
    ExternalDevServer,
    PathConfig,
    RuntimeConfig,
    SPAConfig,
    TypeGenConfig,
    ViteConfig,
)
from litestar_vite.executor import BunExecutor, NodeenvExecutor, NodeExecutor


def test_default_vite_config() -> None:
    config = ViteConfig()
    assert isinstance(config.bundle_dir, Path)
    assert isinstance(config.static_dir, Path)
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
    config = ViteConfig(runtime=RuntimeConfig(health_check=True), base_url="https://cdn.example.com/")
    assert config.health_check is True
    assert config.base_url == "https://cdn.example.com/"


def test_new_config_structure() -> None:
    """Test the new nested config structure."""
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(bundle_dir=Path("/app/dist"), resource_dir=Path("/app/src")),
        runtime=RuntimeConfig(
            dev_mode=True,
            proxy_mode="vite",  # Use new field
            executor="bun",
        ),
        types=True,  # Shorthand for TypeGenConfig()
    )
    assert config.mode == "spa"
    assert config.bundle_dir == Path("/app/dist")
    assert config.resource_dir == Path("/app/src")
    assert config.is_dev_mode is True
    assert config.hot_reload is True  # Derived from proxy_mode
    assert isinstance(config.types, TypeGenConfig)  # Presence = enabled
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


def test_proxy_mode_defaults_to_vite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test proxy_mode defaults to vite."""
    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)

    config = RuntimeConfig()

    assert config.proxy_mode == "vite"


def test_proxy_mode_respects_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_PROXY_MODE=direct maps to direct."""
    monkeypatch.setenv("VITE_PROXY_MODE", "direct")

    config = RuntimeConfig()

    assert config.proxy_mode == "direct"


def test_proxy_mode_respects_none_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_PROXY_MODE=none disables proxy."""
    monkeypatch.setenv("VITE_PROXY_MODE", "none")

    config = RuntimeConfig()

    assert config.proxy_mode is None


def test_proxy_mode_respects_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test VITE_PROXY_MODE=proxy is recognized."""
    monkeypatch.setenv("VITE_PROXY_MODE", "proxy")

    config = RuntimeConfig(external_dev_server="http://localhost:4200")

    assert config.proxy_mode == "proxy"


@pytest.mark.parametrize("value", ["vite_direct", "ssr", "external_proxy", "external", "disabled", "off", ""])
def test_proxy_mode_invalid_env_raises(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """Test legacy/invalid VITE_PROXY_MODE values raise (no compatibility aliases)."""
    monkeypatch.setenv("VITE_PROXY_MODE", value)
    with pytest.raises(ValueError, match="VITE_PROXY_MODE"):
        RuntimeConfig()


# ============================================================================
# ExternalDevServer tests
# ============================================================================


def test_external_dev_server_defaults() -> None:
    """Test ExternalDevServer has sensible defaults."""
    ext = ExternalDevServer()

    assert ext.target is None  # None = dynamic target via hotfile
    assert ext.http2 is False
    assert ext.enabled is True


def test_external_dev_server_custom_values() -> None:
    """Test ExternalDevServer with custom values."""
    ext = ExternalDevServer(target="http://localhost:3000", http2=True, enabled=False)

    assert ext.target == "http://localhost:3000"
    assert ext.http2 is True
    assert ext.enabled is False


def test_typegen_config_defaults_from_output_path() -> None:
    config = TypeGenConfig(output=cast(Path, "src/generated"))
    assert config.output == Path("src/generated")
    assert config.openapi_path == Path("src/generated/openapi.json")
    assert config.routes_path == Path("src/generated/routes.json")
    assert config.routes_ts_path == Path("src/generated/routes.ts")
    assert config.page_props_path == Path("src/generated/inertia-pages.json")
    assert config.schemas_ts_path == Path("src/generated/schemas.ts")


def test_typegen_config_string_paths_normalize() -> None:
    config = TypeGenConfig(
        output=cast(Path, "src/generated"),
        openapi_path=cast(Path, "openapi.json"),
        routes_path=cast(Path, "routes.json"),
        routes_ts_path=cast(Path, "routes.ts"),
        page_props_path=cast(Path, "pages.json"),
        schemas_ts_path=cast(Path, "schemas.ts"),
    )
    assert config.openapi_path == Path("openapi.json")
    assert config.routes_path == Path("routes.json")
    assert config.routes_ts_path == Path("routes.ts")
    assert config.page_props_path == Path("pages.json")
    assert config.schemas_ts_path == Path("schemas.ts")


def test_runtime_config_external_dev_server_string_normalization() -> None:
    """Test external_dev_server string is normalized to ExternalDevServer."""
    config = RuntimeConfig(proxy_mode="proxy", external_dev_server="http://localhost:3000")

    assert isinstance(config.external_dev_server, ExternalDevServer)
    assert config.external_dev_server.target == "http://localhost:3000"


def test_runtime_config_external_dev_server_object() -> None:
    """Test external_dev_server can be passed as object."""
    ext = ExternalDevServer(target="http://localhost:4200", http2=True)
    config = RuntimeConfig(proxy_mode="proxy", external_dev_server=ext)

    assert config.external_dev_server is ext
    assert isinstance(config.external_dev_server, ExternalDevServer)
    assert config.external_dev_server.http2 is True


def test_runtime_config_proxy_mode_without_target() -> None:
    """Test proxy mode works without external_dev_server (uses hotfile)."""
    # No longer raises - proxy mode can read target URL from hotfile
    config = RuntimeConfig(proxy_mode="proxy", external_dev_server=None)
    assert config.proxy_mode == "proxy"
    assert config.external_dev_server is None


def test_vite_config_proxy_mode() -> None:
    """Test ViteConfig with proxy mode."""
    config = ViteConfig(
        runtime=RuntimeConfig(
            dev_mode=True, proxy_mode="proxy", external_dev_server=ExternalDevServer(target="http://localhost:4200")
        )
    )

    assert config.proxy_mode == "proxy"
    assert config.external_dev_server is not None
    assert config.external_dev_server.target == "http://localhost:4200"
    # HMR is now supported in proxy mode (SSR frameworks use Vite internally)
    assert config.hot_reload is True


def test_hot_reload_derived_from_vite_mode() -> None:
    """Test hot_reload is True for vite mode."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode="vite"))

    assert config.hot_reload is True


def test_hot_reload_derived_from_direct_mode() -> None:
    """Test hot_reload is True for direct mode."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, proxy_mode="direct"))

    assert config.hot_reload is True


def test_hot_reload_enabled_for_proxy_mode() -> None:
    """Test hot_reload is True for proxy mode (SSR frameworks use Vite internally)."""
    config = ViteConfig(
        runtime=RuntimeConfig(dev_mode=True, proxy_mode="proxy", external_dev_server="http://localhost:4200")
    )

    # HMR is now supported in proxy mode since SSR frameworks use Vite internally
    assert config.hot_reload is True


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

    config = ViteConfig(mode="spa", paths=PathConfig(resource_dir=resource_dir), dev_mode=False)

    with pytest.raises(ValueError, match=r"SPA mode requires index\.html"):
        config.validate_mode()


def test_type_paths_resolve_relative_and_cascade(tmp_path: Path) -> None:
    """TypeGen paths resolve under paths.root and cascade when only output is set."""
    root = tmp_path / "js"
    config = ViteConfig(
        paths=PathConfig(root=root),
        types=TypeGenConfig(
            output=Path("src/generated/types")  # only output overridden
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


def test_has_built_assets_detects_manifest_in_vite_dir(tmp_path: Path) -> None:
    """Built-asset detection should include bundle_dir/.vite/manifest.json."""
    bundle_dir = tmp_path / "dist"
    (bundle_dir / ".vite").mkdir(parents=True)
    (bundle_dir / ".vite" / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')

    config = ViteConfig(mode="spa", dev_mode=False, paths=PathConfig(bundle_dir=bundle_dir))

    assert config.has_built_assets() is True


def test_validate_mode_spa_dev_mode_allows_missing_index(tmp_path: Path) -> None:
    """Test validation passes for SPA mode in dev mode even without index.html."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()

    config = ViteConfig(mode="spa", paths=PathConfig(resource_dir=resource_dir), dev_mode=True)

    # Should not raise
    config.validate_mode()


def test_asset_url_uses_deploy_asset_url_in_production() -> None:
    config = ViteConfig(
        deploy=DeployConfig(enabled=True, asset_url="https://cdn.example.com/assets/"),
        dev_mode=False,
        paths=PathConfig(asset_url="https://runtime.example.com/static/"),
    )

    # Deploy asset_url should not change runtime asset_url; it's used for build-time base via `.litestar.json`.
    assert config.asset_url == "https://runtime.example.com/static/"


def test_asset_url_ignores_deploy_asset_url_in_dev_mode() -> None:
    config = ViteConfig(deploy=DeployConfig(enabled=True, asset_url="https://cdn.example.com/assets/"), dev_mode=True)

    # Dev mode should keep the normal asset_url (default /static/)
    assert config.asset_url == "/static/"


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

    assert spa_config.inject_csrf is True
    assert spa_config.csrf_var_name == "__LITESTAR_CSRF__"
    assert spa_config.app_selector == "#app"
    assert spa_config.cache_transformed_html is True


def test_spa_config_custom_values() -> None:
    """Test SPAConfig with custom values."""
    spa_config = SPAConfig(
        inject_csrf=False, csrf_var_name="CSRF_TOKEN", app_selector="#root", cache_transformed_html=False
    )

    assert spa_config.inject_csrf is False
    assert spa_config.csrf_var_name == "CSRF_TOKEN"
    assert spa_config.app_selector == "#root"
    assert spa_config.cache_transformed_html is False


def test_vite_config_spa_bool_shortcut() -> None:
    """Test spa=True creates SPAConfig with defaults."""
    config = ViteConfig(spa=True)

    assert isinstance(config.spa, SPAConfig)
    assert config.spa_config is not None
    assert config.spa_config.inject_csrf is True
    assert config.spa_config.csrf_var_name == "__LITESTAR_CSRF__"


def test_vite_config_spa_false() -> None:
    """Test spa=False explicitly disables SPA config."""
    config = ViteConfig(mode="spa", spa=False)

    assert config.spa is False
    assert config.spa_config is None


def test_vite_config_spa_explicit_config() -> None:
    """Test spa can be set to an explicit SPAConfig."""
    spa_config = SPAConfig(csrf_var_name="__CUSTOM_CSRF__", app_selector="#custom-app")
    config = ViteConfig(spa=spa_config)

    assert config.spa is spa_config
    assert config.spa_config is spa_config
    assert config.spa_config.csrf_var_name == "__CUSTOM_CSRF__"
    assert config.spa_config.app_selector == "#custom-app"


def test_vite_config_spa_auto_enabled_for_spa_mode(tmp_path: Path) -> None:
    """Test that SPAConfig is auto-enabled when mode='spa'."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    # Don't explicitly set spa - it should be auto-enabled for mode="spa"
    config = ViteConfig(mode="spa", paths=PathConfig(resource_dir=resource_dir))

    assert isinstance(config.spa, SPAConfig)
    assert config.spa_config is not None
    assert config.spa_config.inject_csrf is True


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


# ============================================================================
# Hybrid mode tests
# ============================================================================


def test_hybrid_mode_explicit() -> None:
    """Test that mode='hybrid' can be explicitly set."""
    from litestar_vite.inertia import InertiaConfig

    config = ViteConfig(mode="hybrid", inertia=InertiaConfig())

    assert config.mode == "hybrid"
    # Hybrid mode should auto-enable SPAConfig like spa mode
    assert isinstance(config.spa, SPAConfig)
    assert config.spa_config is not None


def test_hybrid_mode_auto_detected_with_inertia() -> None:
    """Test that hybrid mode is auto-detected when Inertia is enabled."""
    from litestar_vite.inertia import InertiaConfig

    config = ViteConfig(inertia=InertiaConfig())

    assert config.mode == "hybrid"
    assert config._mode_auto_detected is True


def test_hybrid_mode_auto_detected_with_index_html(tmp_path: Path) -> None:
    """Test that hybrid mode is auto-detected when Inertia enabled + index.html exists."""
    from litestar_vite.inertia import InertiaConfig

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    # No spa_mode set - should auto-detect hybrid from index.html
    config = ViteConfig(
        paths=PathConfig(resource_dir=resource_dir),
        inertia=InertiaConfig(),  # No spa_mode=True needed!
    )

    assert config.mode == "hybrid"
    assert config._mode_auto_detected is True


def test_hybrid_mode_auto_detected_when_inertia_enabled(tmp_path: Path) -> None:
    """Test that hybrid mode is auto-detected when InertiaConfig is present.

    When InertiaConfig is provided, we default to hybrid mode because:
    1. In dev mode, Vite dev server serves the index.html
    2. In production, built assets include index.html
    Users who want Jinja2 templates with Inertia should set mode="template" explicitly.
    """
    from litestar_vite.inertia import InertiaConfig

    # Empty directory - no index.html (doesn't matter, defaults to hybrid)
    config = ViteConfig(paths=PathConfig(resource_dir=tmp_path), inertia=InertiaConfig())

    assert config.mode == "hybrid"
    assert config._mode_auto_detected is True


def test_hybrid_mode_validation_requires_index_html(tmp_path: Path) -> None:
    """Test that hybrid mode validation requires index.html in production."""
    from litestar_vite.inertia import InertiaConfig

    # Empty directory - no index.html
    config = ViteConfig(mode="hybrid", paths=PathConfig(resource_dir=tmp_path), inertia=InertiaConfig())

    with pytest.raises(ValueError, match=r"Hybrid mode requires index\.html"):
        config.validate_mode()


def test_hybrid_mode_validation_passes_in_dev_mode(tmp_path: Path) -> None:
    """Test that hybrid mode validation passes in dev mode without index.html."""
    from litestar_vite.inertia import InertiaConfig

    # Empty directory - no index.html, but dev_mode=True
    config = ViteConfig(mode="hybrid", dev_mode=True, paths=PathConfig(resource_dir=tmp_path), inertia=InertiaConfig())

    # Should not raise
    config.validate_mode()


def test_hybrid_mode_validation_passes_with_index_html(tmp_path: Path) -> None:
    """Test that hybrid mode validation passes when index.html exists."""
    from litestar_vite.inertia import InertiaConfig

    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html></html>")

    config = ViteConfig(
        mode="hybrid",
        paths=PathConfig(resource_dir=resource_dir),
        inertia=InertiaConfig(),  # Auto-detects hybrid from index.html
    )

    # Should not raise
    config.validate_mode()


def test_inertia_presence_means_enabled(tmp_path: Path) -> None:
    """Test that presence of InertiaConfig means Inertia is enabled."""
    from litestar_vite.inertia import InertiaConfig

    # Passing InertiaConfig instance means enabled
    # Defaults to hybrid mode regardless of index.html presence
    config = ViteConfig(paths=PathConfig(resource_dir=tmp_path), inertia=InertiaConfig())
    assert isinstance(config.inertia, InertiaConfig)
    assert config.mode == "hybrid"  # InertiaConfig present → hybrid

    # Passing True enables with defaults
    config2 = ViteConfig(paths=PathConfig(resource_dir=tmp_path), inertia=True)
    assert isinstance(config2.inertia, InertiaConfig)
    assert config2.mode == "hybrid"

    # Passing False/None means disabled
    config3 = ViteConfig(inertia=False)
    assert config3.inertia is None

    config4 = ViteConfig(inertia=None)
    assert config4.inertia is None


# ============================================================================
# Mode alias tests
# ============================================================================


def test_mode_alias_ssg_to_framework() -> None:
    """Test that mode='ssg' is normalized to 'framework'."""
    config = ViteConfig(mode="ssg")

    assert config.mode == "framework"


def test_mode_alias_inertia_to_hybrid() -> None:
    """Test that mode='inertia' is normalized to 'hybrid'."""
    config = ViteConfig(mode="inertia")

    assert config.mode == "hybrid"
    # Hybrid mode should auto-enable SPAConfig
    assert isinstance(config.spa, SPAConfig)
