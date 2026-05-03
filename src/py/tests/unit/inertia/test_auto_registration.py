"""Regression tests for InertiaPlugin auto-registration via VitePlugin.

These tests guard against the 0.22.2 regression in which
``VitePlugin._configure_inertia`` constructed an ``InertiaPlugin`` and
appended it to ``app_config.plugins``, then relied on Litestar's plugin
iterator to call its ``on_app_init`` later. That hand-off silently broke
when other plugins rebound ``app_config.plugins`` to a fresh list, leaving
the iterator stuck on the original list and the InertiaPlugin un-initialized.

The fix is two-part:

1. ``VitePlugin._configure_inertia`` invokes ``inertia_plugin.on_app_init``
   eagerly instead of waiting for Litestar's iterator.
2. ``InertiaPlugin.on_app_init`` is idempotent so the eager call plus a
   subsequent iterator-driven call is safe (no double middleware/lifespan).
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from litestar import Request, get
from litestar.config.app import AppConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins import InitPluginProtocol
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.middleware import InertiaMiddleware
from litestar_vite.plugin import VitePlugin


@pytest.fixture
def inertia_vite_config(test_app_path: Path) -> ViteConfig:
    """ViteConfig with inertia configured -- exercises ``_configure_inertia``."""
    return ViteConfig(
        mode="template",
        paths=PathConfig(bundle_dir=test_app_path / "public", resource_dir=test_app_path / "resources"),
        runtime=RuntimeConfig(dev_mode=True),
        inertia=InertiaConfig(root_template="index.html.j2"),
    )


@pytest.fixture
def template_config_inertia(test_app_path: Path) -> TemplateConfig[Any]:
    """Template config that points at the Inertia test templates folder."""
    from litestar.contrib.jinja import JinjaTemplateEngine

    return TemplateConfig(engine=JinjaTemplateEngine(directory=Path(__file__).parent / "templates"))


def _handler_kwargs(template_config: TemplateConfig[Any]) -> dict[str, Any]:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"thing": "value"}

    return {
        "route_handlers": [handler],
        "template_config": template_config,
        "middleware": [ServerSideSessionConfig().middleware],
        "stores": {"sessions": MemoryStore()},
    }


def test_inertia_plugin_registered_via_vite_config(
    inertia_vite_config: ViteConfig, template_config_inertia: TemplateConfig[Any]
) -> None:
    """``app.plugins.get(InertiaPlugin)`` must work when configured via ViteConfig.inertia."""
    with create_test_client(
        plugins=[VitePlugin(config=inertia_vite_config)], **_handler_kwargs(template_config_inertia)
    ) as client:
        plugin = client.app.plugins.get(InertiaPlugin)
        assert isinstance(plugin, InertiaPlugin)


def test_inertia_envelope_returned_when_auto_registered(
    inertia_vite_config: ViteConfig, template_config_inertia: TemplateConfig[Any]
) -> None:
    """A request with X-Inertia must return an Inertia-shaped JSON body.

    This is the smoking-gun symptom from the bug report: when the iterator
    hand-off broke, InertiaResponse was never installed and JSON requests
    returned the raw handler dict instead of the Inertia envelope.
    """
    with create_test_client(
        plugins=[VitePlugin(config=inertia_vite_config)], **_handler_kwargs(template_config_inertia)
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Envelope keys -- if InertiaPlugin.on_app_init never ran, response_class
        # is still the default Response and these keys would be absent.
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert "version" in data
        assert data["props"]["thing"] == "value"


def test_inertia_html_shell_uses_template_render(
    inertia_vite_config: ViteConfig, template_config_inertia: TemplateConfig[Any]
) -> None:
    """A non-Inertia GET must render through the Jinja template shell.

    Pre-fix, with InertiaPlugin un-initialized, the response would NOT go
    through InertiaResponse and the shell would not be rendered -- instead
    the raw handler dict would be JSON-serialized.
    """
    with create_test_client(
        plugins=[VitePlugin(config=inertia_vite_config)], **_handler_kwargs(template_config_inertia)
    ) as client:
        response = client.get("/")
        assert response.text.startswith("<!DOCTYPE html>")
        # The shell template carries the data-page hook on the root element.
        assert 'data-page="' in response.text


def test_inertia_middleware_installed_only_once(
    inertia_vite_config: ViteConfig, template_config_inertia: TemplateConfig[Any]
) -> None:
    """Eager + iterator double-call must not stack InertiaMiddleware twice.

    InertiaPlugin.on_app_init is idempotent; this test guards that property.
    """
    with create_test_client(
        plugins=[VitePlugin(config=inertia_vite_config)], **_handler_kwargs(template_config_inertia)
    ) as client:
        middleware_classes = [
            getattr(mw, "middleware", mw)
            for mw in client.app.middleware  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
        ]
        # InertiaMiddleware is appended as a class (not DefineMiddleware).
        count = sum(1 for mw in middleware_classes if mw is InertiaMiddleware)
        assert count == 1, f"InertiaMiddleware registered {count} times, expected 1"


class _ReboundPlugin(InitPluginProtocol):
    """Test double for plugins (e.g. older SQLSpecPlugin) that rebind plugins.

    This reproduces the exact failure mode from the bug report: a plugin that
    runs before VitePlugin and rebinds ``app_config.plugins`` to a fresh list.
    Litestar's plugin iterator captures the original list reference, so any
    plugins VitePlugin appends to the new list are skipped by the iterator.
    """

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.plugins = list(app_config.plugins)  # rebind to fresh list
        return app_config


@pytest.mark.parametrize(
    "ordering",
    [
        pytest.param("vite_alone", id="vite-alone"),
        pytest.param("vite_then_other", id="vite-then-rebinder"),
        pytest.param("other_then_vite", id="rebinder-then-vite"),
    ],
)
def test_inertia_works_under_plugin_orderings(
    ordering: str, inertia_vite_config: ViteConfig, template_config_inertia: TemplateConfig[Any]
) -> None:
    """The fix must hold regardless of ordering relative to a list-rebinding plugin.

    Pre-fix, the ``rebinder-then-vite`` ordering broke silently because the
    InertiaPlugin appended by VitePlugin landed in a list the iterator no
    longer saw.
    """
    vite_plugin = VitePlugin(config=inertia_vite_config)
    if ordering == "vite_alone":
        plugins: list[Any] = [vite_plugin]
    elif ordering == "vite_then_other":
        plugins = [vite_plugin, _ReboundPlugin()]
    else:  # other_then_vite
        plugins = [_ReboundPlugin(), vite_plugin]

    with create_test_client(plugins=plugins, **_handler_kwargs(template_config_inertia)) as client:
        # Registry lookup
        assert isinstance(client.app.plugins.get(InertiaPlugin), InertiaPlugin)
        # Inertia envelope
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        assert data["component"] == "Home"
        assert data["props"]["thing"] == "value"


def test_inertia_plugin_on_app_init_is_idempotent(inertia_vite_config: ViteConfig) -> None:
    """Calling on_app_init twice on the same instance must be a no-op the second time.

    This is the contract VitePlugin._configure_inertia relies on for safety
    when both the eager call and Litestar's iterator end up invoking it.
    """
    plugin = InertiaPlugin(config=inertia_vite_config.inertia)  # type: ignore[arg-type]

    config = AppConfig(middleware=[ServerSideSessionConfig().middleware], stores={"sessions": MemoryStore()})
    config = plugin.on_app_init(config)
    middleware_count_after_first = len(config.middleware)
    lifespan_count_after_first = len(config.lifespan)
    on_startup_count_after_first = len(config.on_startup)

    config = plugin.on_app_init(config)

    assert len(config.middleware) == middleware_count_after_first
    assert len(config.lifespan) == lifespan_count_after_first
    assert len(config.on_startup) == on_startup_count_after_first


# Quiet pyright about an unused import -- Iterator is reserved for future params.
_ = Iterator
