"""Integration tests for all example applications.

These tests verify that all example apps can be:
1. Imported without errors
2. Have valid Litestar app instances
3. Have correctly configured VitePlugin
4. Pass basic sanity checks for their mode (SPA, template, SSR, etc.)
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from litestar_vite.plugin import VitePlugin

# Path to examples directory
EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent.parent / "examples"

# All example directories with their expected characteristics
EXAMPLES = [
    # (name, has_spa_mode, has_inertia, is_ssr_framework)
    ("angular", True, False, False),
    ("angular-cli", True, False, False),
    ("astro", False, False, True),  # SSR framework - no SPA mode
    ("jinja-htmx", False, False, False),  # Template mode (HTMX)
    ("nuxt", False, False, True),  # SSR framework - no SPA mode
    ("react", True, False, False),
    ("react-inertia", False, True, False),  # Inertia hybrid mode
    ("react-inertia-jinja", False, True, False),  # Inertia template mode
    ("svelte", True, False, False),
    ("sveltekit", False, False, True),  # SSR framework - no SPA mode
    ("vue", True, False, False),
    ("vue-inertia", False, True, False),  # Inertia hybrid mode
    ("vue-inertia-jinja", False, True, False),  # Inertia template mode
]


def load_app_from_example(example_name: str) -> Litestar:
    """Load a Litestar app from an example directory.

    Args:
        example_name: Name of the example directory.

    Returns:
        The Litestar app instance from the example.
    """
    example_path = EXAMPLES_DIR / example_name
    app_file = example_path / "app.py"

    if not app_file.exists():
        pytest.skip(f"Example {example_name} has no app.py")

    # Load the module
    spec = importlib.util.spec_from_file_location(f"examples.{example_name}.app", app_file)
    if spec is None or spec.loader is None:
        pytest.fail(f"Could not load spec for {app_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[f"examples.{example_name}.app"] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        pytest.fail(f"Failed to load {example_name}/app.py: {e}")

    try:
        return module.app
    except AttributeError:
        pytest.fail(f"Example {example_name} has no 'app' attribute")


def get_vite_plugin(app: Litestar) -> VitePlugin | None:
    """Extract VitePlugin from a Litestar app.

    Returns:
        The vite plugin.
    """
    for plugin in app.plugins:
        if isinstance(plugin, VitePlugin):
            return plugin
    return None


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_app_loads(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example app can be loaded and has valid structure."""
    app = load_app_from_example(example_name)

    # Basic checks
    assert isinstance(app, Litestar), f"{example_name}: app should be a Litestar instance"

    # Check VitePlugin is present
    vite_plugin = get_vite_plugin(app)
    assert vite_plugin is not None, f"{example_name}: should have VitePlugin configured"

    # Check config exists
    config = vite_plugin.config
    assert config is not None, f"{example_name}: VitePlugin should have config"


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_config_mode(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example has correct mode configuration."""
    app = load_app_from_example(example_name)
    vite_plugin = get_vite_plugin(app)
    assert vite_plugin is not None

    config = vite_plugin.config

    if is_ssr:
        # SSR frameworks (Astro, Nuxt, SvelteKit) should NOT have spa_handler enabled
        # because they handle their own routing
        assert not config.spa_handler, (
            f"{example_name}: SSR framework should not have spa_handler enabled. "
            f"Set spa=False or mode='template' for SSR frameworks."
        )

    if has_inertia:
        # Inertia apps should have inertia config
        assert config.inertia is not None or config.mode != "spa", (
            f"{example_name}: Inertia app should have inertia config or non-spa mode"
        )


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_paths_config(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example has valid paths configuration."""
    app = load_app_from_example(example_name)
    vite_plugin = get_vite_plugin(app)
    assert vite_plugin is not None

    config = vite_plugin.config

    # Root path should be set and exist (accessed via paths.root)
    root_path = Path(config.paths.root) if config.paths.root else None
    assert root_path is not None, f"{example_name}: root path should be set"
    assert root_path.exists(), f"{example_name}: root path {root_path} should exist"

    # Root should be the example directory (not cwd which could be anywhere)
    expected_root = EXAMPLES_DIR / example_name
    assert root_path == expected_root, (
        f"{example_name}: root path should be {expected_root}, got {root_path}. "
        f"Set paths=PathConfig(root=Path(__file__).parent) in ViteConfig."
    )


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_api_endpoints(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example API endpoints work (for examples that have them)."""
    app = load_app_from_example(example_name)

    # Only test apps that have API routes defined
    api_examples = [
        "angular",
        "angular-cli",
        "astro",
        "jinja-htmx",
        "nuxt",
        "react",
        "react-inertia",
        "react-inertia-jinja",
        "svelte",
        "sveltekit",
        "vue",
        "vue-inertia",
        "vue-inertia-jinja",
    ]

    if example_name not in api_examples:
        pytest.skip(f"{example_name} doesn't have standard API endpoints")

    with TestClient(app) as client:
        # Test /api/summary endpoint (common across API examples)
        response = client.get("/api/summary")
        if response.status_code == 200:
            data = response.json()
            assert "app" in data or "headline" in data, f"{example_name}: /api/summary should return summary data"
        elif response.status_code == 404:
            # Some examples might not have this exact endpoint
            pass
        else:
            pytest.fail(f"{example_name}: /api/summary returned unexpected status {response.status_code}")


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_dev_mode_config(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example has appropriate dev_mode configuration."""
    app = load_app_from_example(example_name)
    vite_plugin = get_vite_plugin(app)
    assert vite_plugin is not None

    config = vite_plugin.config

    # Dev mode should be explicitly set (True for dev examples)
    # This test just verifies the config is accessible
    assert isinstance(config.dev_mode, bool), f"{example_name}: dev_mode should be a boolean"


@pytest.mark.parametrize("example_name,has_spa,has_inertia,is_ssr", EXAMPLES)
def test_example_proxy_mode_config(example_name: str, has_spa: bool, has_inertia: bool, is_ssr: bool) -> None:
    """Test that example has correct proxy_mode configuration."""
    app = load_app_from_example(example_name)
    vite_plugin = get_vite_plugin(app)
    assert vite_plugin is not None

    config = vite_plugin.config

    # Proxy mode should be one of the valid values or None
    valid_modes = {"vite", "direct", "proxy", None}
    assert config.proxy_mode in valid_modes, (
        f"{example_name}: proxy_mode should be one of {valid_modes}, got {config.proxy_mode}"
    )

    if is_ssr:
        # SSR frameworks should use "proxy" mode for deny list-style proxying that forwards everything except Litestar routes
        assert config.proxy_mode == "proxy", (
            f"{example_name}: SSR framework should use proxy_mode='proxy'. "
            f"Got proxy_mode='{config.proxy_mode}'. "
            f"Set runtime=RuntimeConfig(proxy_mode='proxy') in ViteConfig."
        )

    # Angular CLI example uses "proxy" mode with static target
    if example_name == "angular-cli":
        assert config.proxy_mode == "proxy", f"{example_name}: should use proxy_mode='proxy' for Angular CLI"
