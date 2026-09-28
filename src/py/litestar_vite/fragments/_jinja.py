"""Jinja2 template integration for rendering Vite component fragments."""

import functools
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, cast

import anyio
import markupsafe
from litestar.handlers import HTTPRouteHandler
from litestar.response import Template
from litestar.response.base import ASGIResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar import Litestar
    from litestar.types import ASGIApp, Receive, Scope, Send

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


class _DeferredTemplateResponse(ASGIResponse):
    """Hold a synchronous template render until its converter can await it."""

    __slots__ = ("_render_template",)

    def __init__(self, render_template: "Callable[[], ASGIResponse]") -> None:
        super().__init__()
        self._render_template = render_template

    async def render_async(self) -> ASGIResponse:
        return await anyio.to_thread.run_sync(self._render_template)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = await self.render_async()
        await response(scope, receive, send)


class _AsyncFragmentTemplate(Template):
    """Allow the response converter to render Jinja in an AnyIO worker thread."""

    __slots__ = ()

    def to_asgi_response(self, *args: Any, **kwargs: Any) -> ASGIResponse:
        return _DeferredTemplateResponse(
            functools.partial(super().to_asgi_response, *args, **kwargs)  # pyright: ignore[reportUnknownMemberType]
        )


def _wrap_template_converter(handler: HTTPRouteHandler) -> None:
    """Adapt Litestar's synchronous Template conversion at its async boundary.

    The response converter runs inside Litestar's dependency cleanup scope,
    after the handler and its after_request hook and before caching/compression.
    A middleware or deferred ASGI render would run too late. Keep the private
    converter mapping access here so this integration has one compatibility seam.
    """
    original = cast("Callable[..., Awaitable[ASGIApp]]", handler.get_response_handler(is_response_type_data=True))
    if getattr(original, "_vite_fragment_template_wrapped", False):
        return

    @functools.wraps(original)
    async def convert(data: Any, **kwargs: Any) -> "ASGIApp":
        if type(data) is Template:
            template = _AsyncFragmentTemplate(
                template_name=data.template_name,
                template_str=data.template_str,
                context=data.context,
                background=data.background,
                cookies=data.cookies,
                encoding=data.encoding,
                headers=data.headers,
                media_type=data.media_type,
                status_code=data.status_code or 200,
            )
            template.status_code = data.status_code
            template.response_type_encoders = data.response_type_encoders
            data = template
        response = await original(data=data, **kwargs)
        if isinstance(response, _DeferredTemplateResponse):
            return await response.render_async()
        return response

    convert._vite_fragment_template_wrapped = True  # type: ignore[attr-defined]
    handler._response_handler_mapping["response_type_handler"] = convert  # pyright: ignore[reportPrivateUsage]


def wrap_fragment_template_handlers(app: "Litestar") -> None:
    """Enable asynchronous fragment rendering for standard Template responses."""
    for route in app.routes:
        for handler in getattr(route, "route_handlers", ()):
            if isinstance(handler, HTTPRouteHandler):
                _wrap_template_converter(handler)
