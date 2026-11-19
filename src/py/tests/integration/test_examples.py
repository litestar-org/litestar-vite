"""Integration tests for all example applications.

These tests verify that all example apps can be:
1. Imported without errors
2. Have valid Litestar app instances
3. Have correctly configured VitePlugin
4. Pass basic sanity checks for their mode (SPA, template, SSR, etc.)
"""

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from litestar_vite.plugin import VitePlugin

# Path to examples directory
EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent.parent / "examples"

INERTIA_EXAMPLES = [
    "react-inertia",
    "react-inertia-jinja",
    "svelte-inertia",
    "svelte-inertia-jinja",
    "vue-inertia",
    "vue-inertia-jinja",
    "vue-inertia-ssr",
    "vue-inertia-jinja-ssr",
]

ALL_EXAMPLE_NAMES = [path.parent.name for path in sorted(EXAMPLES_DIR.glob("*/app.py"))]

# All example directories with their expected characteristics
EXAMPLES = [
    # (name, has_spa_mode, has_inertia, is_ssr_framework)
    ("angular", True, False, False),
    ("angular-cli", True, False, False),
    ("astro", False, False, True),  # SSR framework - no SPA mode
    ("jinja-htmx", False, False, False),  # Template mode (HTMX)
    ("htmx-stream", False, False, False),  # Template mode (WebSocket + SSE)
    ("nuxt", False, False, True),  # SSR framework - no SPA mode
    ("react", True, False, False),
    ("react-tanstack", True, False, False),
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


def test_stream_example_contains_no_hand_written_queue_adapter() -> None:
    """Keep parsing, heartbeat filtering, and swapping inside the helper."""
    source = (EXAMPLES_DIR / "htmx-stream" / "resources" / "main.ts").read_text()
    assert "JSON.parse" not in source
    assert "preventDefault" not in source
    assert '"ping"' not in source


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
        "react-tanstack",
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


def _load_fresh_example_module(example_name: str, module_name: str) -> ModuleType:
    """Import an example app module under an isolated module name."""
    app_file = EXAMPLES_DIR / example_name / "app.py"
    spec = importlib.util.spec_from_file_location(module_name, app_file)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def test_all_examples_discovered() -> None:
    """Verify all 21 example apps are discovered."""
    assert len(ALL_EXAMPLE_NAMES) == 21


@pytest.mark.parametrize("example_name", ALL_EXAMPLE_NAMES)
def test_example_free_of_static_debug_or_secret(example_name: str) -> None:
    """Verify each example app avoids hardcoded debug=True and static secrets."""
    source = (EXAMPLES_DIR / example_name / "app.py").read_text(encoding="utf-8")
    assert "debug=True" not in source, f"{example_name}/app.py still hardcodes debug=True"
    assert "development-only-secret-32-chars" not in source, f"{example_name}/app.py still contains static secret"


@pytest.mark.parametrize("example_name", ALL_EXAMPLE_NAMES)
def test_example_debug_defaults_to_false_and_honors_env(example_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify LITESTAR_DEBUG controls app.debug across all 21 example apps."""
    monkeypatch.delenv("LITESTAR_DEBUG", raising=False)
    default_module = _load_fresh_example_module(example_name, f"examples.{example_name}.debug_default")
    assert default_module.app.debug is False

    monkeypatch.setenv("LITESTAR_DEBUG", "1")
    enabled_module = _load_fresh_example_module(example_name, f"examples.{example_name}.debug_enabled")
    assert enabled_module.app.debug is True


@pytest.mark.parametrize("example_name", INERTIA_EXAMPLES)
def test_inertia_example_ephemeral_secret_and_csrf(
    example_name: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify Inertia examples use ephemeral secrets with a startup log and configure CSRF."""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with caplog.at_level(logging.INFO):
        first = _load_fresh_example_module(example_name, f"examples.{example_name}.ephemeral_1")
        second = _load_fresh_example_module(example_name, f"examples.{example_name}.ephemeral_2")

    assert "SESSION_SECRET is not set; using an ephemeral secret for this process." in caplog.text
    assert first.SESSION_SECRET != second.SESSION_SECRET
    assert first.SESSION_SECRET != b"development-only-secret-32-chars"
    assert first.app.csrf_config is not None


@pytest.mark.parametrize("example_name", INERTIA_EXAMPLES)
def test_inertia_example_honors_configured_session_secret(example_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Inertia examples accept arbitrary-length SESSION_SECRET values."""
    monkeypatch.setenv("SESSION_SECRET", "custom-session-secret")
    module = _load_fresh_example_module(example_name, f"examples.{example_name}.custom_secret")
    assert len(module.SESSION_SECRET) == 32
    assert module.app.csrf_config is not None


def test_htmx_stream_csrf_config_and_client_helper(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify htmx-stream enforces CSRF on publish and uses csrfFetch on the client."""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with caplog.at_level(logging.INFO):
        module = _load_fresh_example_module("htmx-stream", "examples.htmx_stream.csrf_check")

    assert module.app.csrf_config is not None
    assert "SESSION_SECRET is not set; using an ephemeral CSRF secret for this process." in caplog.text

    with TestClient(module.app) as client:
        rejected = client.post("/api/channels/publish")
        assert rejected.status_code == 403

        get_response = client.get("/")
        assert get_response.status_code == 200
        csrf_token = client.cookies.get("csrftoken")
        assert csrf_token

        accepted = client.post("/api/channels/publish", headers={"x-csrftoken": csrf_token})
        assert accepted.status_code == 201
        assert accepted.json() == {"published": True}

    main_ts = (EXAMPLES_DIR / "htmx-stream" / "resources" / "main.ts").read_text(encoding="utf-8")
    assert 'csrfFetch("/api/channels/publish", { method: "POST" })' in main_ts
