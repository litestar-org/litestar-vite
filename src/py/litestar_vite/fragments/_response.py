"""ComponentResponse for server-rendered UI component fragments."""

import contextlib
import uuid
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import ASGIResponse, Response
from litestar.serialization import encode_json
from litestar.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.types import ResponseCookies, ResponseHeaders

__all__ = ("ComponentResponse",)

_ISLAND_CLIENT_SCRIPT: str = (
    '<script type="module">\n'
    'if (typeof window !== "undefined" && !customElements.get("vite-island")) {\n'
    '  customElements.define("vite-island", class extends HTMLElement {\n'
    "    async connectedCallback() {\n"
    '      const compPath = this.getAttribute("data-island-component")\n'
    '      const rawProps = this.getAttribute("data-island-props")\n'
    "      if (!compPath) return\n"
    "      const props = rawProps ? JSON.parse(rawProps) : {}\n"
    "      const mod = await import(/* @vite-ignore */ compPath)\n"
    "      const Component = mod.default || mod\n"
    '      if (typeof Component.hydrate === "function") {\n'
    "        Component.hydrate({ target: this, props })\n"
    "      }\n"
    "    }\n"
    "  })\n"
    "}\n"
    "</script>"
)


class ComponentResponse(Response[str]):
    """HTTP Response that renders a server-side component fragment.

    Renders UI component fragments (React, Vue, Svelte, Astro) into HTML
    markup for HTMX partial swaps and micro-frontend architectures.
    """

    __slots__ = ("component", "mode", "props")

    def __init__(
        self,
        component: str,
        props: dict[str, Any] | None = None,
        mode: Literal["static", "island"] = "static",
        status_code: int = HTTP_200_OK,
        headers: "ResponseHeaders | None" = None,
        cookies: "ResponseCookies | None" = None,
        background: "BackgroundTask | BackgroundTasks | None" = None,
        encoding: str = "utf-8",
    ) -> None:
        """Initialize the ComponentResponse.

        Args:
            component: Path to the component entrypoint.
            props: Optional dictionary of component props.
            mode: Rendering mode ('static' for zero JS or 'island' for interactive).
            status_code: HTTP response status code, defaults to 200.
            headers: Optional dictionary or sequence of response headers.
            cookies: Optional response cookies.
            background: Optional background task to execute after response completion.
            encoding: Content character encoding, defaults to 'utf-8'.
        """
        super().__init__(
            content="",
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            background=background,
            encoding=encoding,
            media_type=MediaType.HTML,
        )
        self.component = component
        self.props = props or {}
        self.mode = mode

    def to_asgi_response(
        self,
        app: Any,
        request: "Request[Any, Any, Any]",
        *,
        background: "BackgroundTask | BackgroundTasks | None" = None,
        cookies: Any = None,
        encoded_headers: Any = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: Any = None,
        status_code: int | None = None,
        type_encoders: Any = None,
    ) -> ASGIResponse:
        """Construct the ASGI response that renders the component fragment.

        Args:
            app: The Litestar application instance.
            request: The incoming request.
            background: Optional background tasks.
            cookies: Optional cookies.
            encoded_headers: Optional encoded headers.
            headers: Optional headers dictionary.
            is_head_response: Whether the request is a HEAD request.
            media_type: Response media type.
            status_code: Optional status code override.
            type_encoders: Type encoders mapping.

        Returns:
            An ASGIResponse callable that executes the fragment rendering.
        """
        from litestar_vite.plugin import VitePlugin

        resolved_headers = self.headers if headers is None else {**headers, **self.headers}
        resolved_status = status_code if status_code is not None else self.status_code

        async def asgi_app(scope: Any, receive: Any, send: Any) -> None:
            plugins: Any = getattr(request.app, "plugins", None)
            vite_plugin: Any = None
            if plugins is not None:
                with contextlib.suppress(KeyError, AttributeError):
                    vite_plugin = plugins.get(VitePlugin)
                if vite_plugin is None:
                    with contextlib.suppress(KeyError, AttributeError):
                        vite_plugin = plugins.get("VitePlugin")
            if vite_plugin is None:
                msg = "VitePlugin must be registered on the application to render ComponentResponse."
                raise ImproperlyConfiguredException(msg)

            rendered_html: str = ""
            render_fn: Any = getattr(vite_plugin, "render_fragment", None)
            if callable(render_fn):
                coro = cast("Callable[..., Awaitable[Any]]", render_fn)(
                    component=self.component, props=self.props, mode=self.mode
                )
                rendered_html = str(await coro)
            else:
                engine_obj: Any = getattr(vite_plugin, "fragment_engine", None)
                engine_render_fn: Any = getattr(engine_obj, "render_fragment", None) if engine_obj else None
                if callable(engine_render_fn):
                    coro = cast("Callable[..., Awaitable[Any]]", engine_render_fn)(
                        component=self.component, props=self.props, mode=self.mode
                    )
                    rendered_html = str(await coro)
                else:
                    msg = "Active VitePlugin does not support fragment rendering."
                    raise ImproperlyConfiguredException(msg)

            if self.mode == "island":
                if "<vite-island" not in rendered_html:
                    escaped_props = encode_json(self.props).decode(self.encoding).replace('"', "&quot;")
                    island_id = f"island-{uuid.uuid4().hex[:8]}"
                    rendered_html = (
                        f'<vite-island data-island-component="{self.component}" '
                        f'data-island-props="{escaped_props}" id="{island_id}">{rendered_html}</vite-island>'
                    )
                if "customElements.define" not in rendered_html:
                    newline = "\r\n" if "\r\n" in rendered_html else "\n"
                    rendered_html = f"{rendered_html}{newline}{_ISLAND_CLIENT_SCRIPT}"

            body_bytes = rendered_html.encode(self.encoding)
            inner_response = ASGIResponse(
                body=body_bytes,
                status_code=resolved_status,
                headers=resolved_headers,
                cookies=cookies or self.cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                media_type=MediaType.HTML,
                is_head_response=is_head_response,
                background=background or self.background,
            )
            await inner_response(scope, receive, send)

        return cast("ASGIResponse", asgi_app)
