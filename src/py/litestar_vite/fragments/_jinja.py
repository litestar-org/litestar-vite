"""Jinja2 template integration for rendering Vite component fragments."""

from collections.abc import Mapping
from typing import Any, Literal

import markupsafe

__all__ = ("render_fragment", "vite_fragment")


def _resolve_vite_plugin(context: Mapping[str, Any]) -> Any:
    """Resolve VitePlugin instance from template context.

    Args:
        context: The template context.

    Returns:
        The registered VitePlugin instance, or None.
    """
    from litestar_vite.plugin import VitePlugin

    request = context.get("request")
    if request is None:
        return None
    app = getattr(request, "app", None)
    if app is None:
        return None
    try:
        return app.plugins.get(VitePlugin)
    except (KeyError, AttributeError):
        pass
    try:
        return app.plugins.get("VitePlugin")
    except (KeyError, AttributeError):
        return None


def vite_fragment(
    context: Mapping[str, Any],
    /,
    component: str,
    props: dict[str, Any] | None = None,
    mode: Literal["static", "island"] = "static",
    **kwargs: Any,
) -> markupsafe.Markup:
    """Render a component fragment within a Jinja2 template.

    Merges explicit props with keyword arguments passed to the template callable.

    Example in Jinja template:
        {{ vite_fragment("components/UserProfile.vue", user=user) }}
        {{ vite_fragment("components/Counter.tsx", props={"initial": 0}, mode="island") }}

    Args:
        context: The Jinja2 template context containing the request.
        component: Relative path to the component entrypoint.
        props: Optional dictionary of component props.
        mode: Rendering mode ('static' for HTML only or 'island' for interactive).
        **kwargs: Additional props passed as keyword arguments.

    Returns:
        Markup-safe rendered HTML string with scoped styles.
    """
    vite_plugin = _resolve_vite_plugin(context)
    if vite_plugin is None:
        return markupsafe.Markup("")
    combined_props = {**(props or {}), **kwargs}
    if hasattr(vite_plugin, "render_fragment_sync"):
        rendered = vite_plugin.render_fragment_sync(component, props=combined_props, mode=mode)
    elif hasattr(vite_plugin, "fragment_engine"):
        rendered = vite_plugin.fragment_engine.render_fragment_sync(component, props=combined_props, mode=mode)
    else:
        rendered = ""
    return markupsafe.Markup(rendered)


render_fragment = vite_fragment
