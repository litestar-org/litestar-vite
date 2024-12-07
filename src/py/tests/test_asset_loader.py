from __future__ import annotations

from typing import Any, Generator

import pytest
from jinja2 import Environment, FileSystemLoader
from litestar.exceptions import ImproperlyConfiguredException

from litestar_vite.config import ViteConfig
from litestar_vite.loader import ViteAssetLoader


@pytest.fixture
def vite_config() -> Generator[ViteConfig, None, None]:
    """Create a ViteConfig instance for testing."""
    yield ViteConfig(
        bundle_dir="public",
        resource_dir="resources",
        public_dir="public",
        root_dir=".",
        asset_url="/static/",
        dev_mode=False,  # Set to False for testing production mode
    )


@pytest.fixture
def jinja_env(vite_config: ViteConfig) -> Generator[Environment, None, None]:
    """Create a Jinja Environment for testing."""
    loader = FileSystemLoader(searchpath=str(vite_config.resource_dir))
    yield Environment(loader=loader, autoescape=True)


@pytest.fixture
def asset_loader(vite_config: ViteConfig) -> Generator[ViteAssetLoader, None, None]:
    """Create a ViteAssetLoader instance for testing."""
    yield ViteAssetLoader.initialize_loader(config=vite_config)


# Happy path tests for get_hmr_client
@pytest.mark.parametrize(
    "expected_output, test_id",
    [
        # Test with a context that should return an empty string in production mode
        ("", "production_mode"),
    ],
)
def test_get_hmr_client(
    asset_loader: ViteAssetLoader,
    expected_output: str,
    test_id: str,
) -> None:
    # Act
    result = asset_loader.render_hmr_client()

    # Assert
    assert str(result) == expected_output, f"Failed test ID: {test_id}"


# Happy path tests for get_asset_tag
@pytest.mark.parametrize(
    "path, scripts_attrs, expected_output, test_id",
    [
        # Test with realistic values for a single asset path
        (
            "resources/main.ts",
            None,
            '<script type="module" async="" defer="" src="/static/assets/main-l0sNRNKZ.js"></script>',
            "asset_single",
        ),
        # Test with additional script attributes
        (
            "resources/styles.css",
            {"async": "true"},
            '<script async="true" src="/static/assets/styles-l0sNRNKZ.js"></script>',
            "asset_attrs",
        ),
        # Test with realistic values for a list of asset paths
        (
            ["resources/main.ts", "resources/styles.css"],
            None,
            '<script type="module" async="" defer="" src="/static/assets/main-l0sNRNKZ.js"></script><script type="module" async="" defer="" src="/static/assets/styles-l0sNRNKZ.js"></script>',
            "asset_multiple",
        ),
    ],
)
def test_get_asset_tag(
    asset_loader: ViteAssetLoader,
    path: str | list[str],
    scripts_attrs: dict[str, Any] | None,
    expected_output: str,
    test_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mock the manifest content
    mock_manifest = {
        "resources/main.ts": {"file": "assets/main-l0sNRNKZ.js"},
        "resources/styles.css": {"file": "assets/styles-l0sNRNKZ.js"},
    }
    monkeypatch.setattr(asset_loader, "_manifest", mock_manifest)

    # Act
    result = asset_loader.render_asset_tag(path=path, scripts_attrs=scripts_attrs)

    # Assert
    assert str(result) == expected_output, f"Failed test ID: {test_id}"


# Edge case tests for get_asset_tag
@pytest.mark.parametrize(
    "path, scripts_attrs, test_id",
    [
        # Test with an empty path
        ("", None, "asset_blank"),
        # Test with non-existent path
        ("resources/nonexistent.ts", None, "asset_nonexistent"),
    ],
)
def test_get_asset_tag_edge_cases(
    asset_loader: ViteAssetLoader,
    path: str | list[str],
    scripts_attrs: dict[str, Any] | None,
    test_id: str,
) -> None:
    if test_id == "asset_blank":
        result = asset_loader.render_asset_tag(path=path, scripts_attrs=scripts_attrs)
        assert result == "", f"Failed test ID: {test_id}"
    else:
        with pytest.raises(ImproperlyConfiguredException) as exc_info:
            asset_loader.render_asset_tag(path=path, scripts_attrs=scripts_attrs)
        assert "Cannot find" in str(exc_info.value), f"Failed test ID: {test_id}"


# Error case tests for get_asset_tag
@pytest.mark.parametrize(
    "path, scripts_attrs, exception, test_id",
    [
        # Test with invalid path type
        (123, None, ImproperlyConfiguredException, "asset_invalid_path_type"),
        # Test with invalid scripts_attrs type
        ("resources/main.ts", "invalid", ImproperlyConfiguredException, "asset_invalid_attrs_type"),
    ],
)
def test_get_asset_tag_error_cases(
    asset_loader: ViteAssetLoader,
    path: str | list[str],
    scripts_attrs: dict[str, Any] | None,
    exception: type[Exception],
    test_id: str,
) -> None:
    # Act / Assert
    with pytest.raises(exception) as exc_info:
        asset_loader.render_asset_tag(path=path, scripts_attrs=scripts_attrs)
    assert exc_info.type is exception, f"Failed test ID: {test_id}"
