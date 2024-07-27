from __future__ import annotations

import itertools
from collections import defaultdict
from functools import lru_cache
from mimetypes import guess_type
from pathlib import PurePath
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, TypeVar, cast
from urllib.parse import quote

from litestar import Litestar, MediaType, Request, Response
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response import Redirect
from litestar.response.base import ASGIResponse
from litestar.serialization import get_serializer
from litestar.status_codes import HTTP_200_OK, HTTP_303_SEE_OTHER, HTTP_307_TEMPORARY_REDIRECT, HTTP_409_CONFLICT
from litestar.utils.deprecation import warn_deprecation
from litestar.utils.empty import value_or_default
from litestar.utils.helpers import get_enum_string_value
from litestar.utils.scope.state import ScopeState
from markupsafe import Markup

from litestar_vite.inertia._utils import get_headers
from litestar_vite.inertia.types import InertiaHeaderType, PageProps
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import ASGIConnection
    from litestar.connection.base import AuthT, StateT, UserT
    from litestar.types import ResponseCookies, ResponseHeaders, TypeEncodersMap

    from litestar_vite.inertia.request import InertiaRequest
    from litestar_vite.inertia.routes import Routes

    from .plugin import InertiaPlugin

T = TypeVar("T")


def share(
    connection: ASGIConnection[Any, Any, Any, Any],
    key: str,
    value: Any,
) -> None:
    try:
        connection.session.setdefault("_shared", {}).update({key: value})
    except AttributeError:
        msg = "Unable to set `share` session state.  A valid session was not found for this request."
        connection.logger.warning(msg)


def error(
    connection: ASGIConnection[Any, Any, Any, Any],
    key: str,
    message: str,
) -> None:
    try:
        connection.session.setdefault("_errors", {}).update({key: message})
    except AttributeError:
        msg = "Unable to set `error` session state.  A valid session was not found for this request."
        connection.logger.warning(msg)


def get_shared_props(request: ASGIConnection[Any, Any, Any, Any]) -> Dict[str, Any]:  # noqa: UP006
    """Return shared session props for a request


    Be sure to call this before `self.create_template_context` if you would like to include the `flash` message details.
    """
    props: dict[str, Any] = {}
    try:
        error_bag = request.headers.get("X-Inertia-Error-Bag", None)
        errors: dict[str, Any] = request.session.pop("_errors", {})
        props.update(cast("Dict[str,Any]", request.session.pop("_shared", {})))
        flash: dict[str, list[str]] = defaultdict(list)
        for message in cast("List[Dict[str,Any]]", request.session.pop("_messages", [])):
            flash[message["category"]].append(message["message"])

        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
        props.update(inertia_plugin.config.extra_static_page_props)
        for session_prop in inertia_plugin.config.extra_session_page_props:
            if session_prop not in props and session_prop in request.session:
                props[session_prop] = request.session.get(session_prop)
        props["flash"] = flash
        props["errors"] = {error_bag: errors} if error_bag is not None else errors
    except AttributeError:
        msg = "Unable to generate all shared props.  A valid session was not found for this request."
        request.logger.warning(msg)
    props["csrf_token"] = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
    return props


def js_routes_script(js_routes: Routes) -> Markup:
    @lru_cache
    def _markup_safe_json_dumps(js_routes: str) -> Markup:
        js = js_routes.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("'", "\\u0027")
        return Markup(js)

    return Markup(
        dedent(f"""
        <script type="module">
        globalThis.routes = JSON.parse('{_markup_safe_json_dumps(js_routes.formatted_routes)}')
        </script>
        """),
    )


class InertiaResponse(Response[T]):
    """Inertia Response"""

    def __init__(
        self,
        content: T,
        *,
        template_name: str | None = None,
        template_str: str | None = None,
        background: BackgroundTask | BackgroundTasks | None = None,
        context: dict[str, Any] | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: ResponseHeaders | None = None,
        media_type: MediaType | str | None = None,
        status_code: int = HTTP_200_OK,
        type_encoders: TypeEncodersMap | None = None,
    ) -> None:
        """Handle the rendering of a given template into a bytes string.

        Args:
            content: A value for the response body that will be rendered into bytes string.
            template_name: Path-like name for the template to be rendered, e.g. ``index.html``.
            template_str: A string representing the template, e.g. ``tmpl = "Hello <strong>World</strong>"``.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to ``None``.
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: Content encoding
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            media_type: A string or member of the :class:`MediaType <.enums.MediaType>` enum. If not set, try to infer
                the media type based on the template name. If this fails, fall back to ``text/plain``.
            status_code: A value for the response HTTP status code.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
        """
        if template_name and template_str:
            msg = "Either template_name or template_str must be provided, not both."
            raise ValueError(msg)
        self.content = content
        self.background = background
        self.cookies: list[Cookie] = (
            [Cookie(key=key, value=value) for key, value in cookies.items()]
            if isinstance(cookies, Mapping)
            else list(cookies or [])
        )
        self.encoding = encoding
        self.headers: dict[str, Any] = (
            dict(headers) if isinstance(headers, Mapping) else {h.name: h.value for h in headers or {}}
        )
        self.media_type = media_type
        self.status_code = status_code
        self.response_type_encoders = {**(self.type_encoders or {}), **(type_encoders or {})}
        self.context = context or {}
        self.template_name = template_name
        self.template_str = template_str

    def create_template_context(
        self,
        request: Request[UserT, AuthT, StateT],
        page_props: PageProps[T],
        type_encoders: TypeEncodersMap | None = None,
    ) -> dict[str, Any]:
        """Create a context object for the template.

        Args:
            request: A :class:`Request <.connection.Request>` instance.
            page_props: A formatted object to return the inertia configuration.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.

        Returns:
            A dictionary holding the template context
        """
        csrf_token = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
        inertia_props = self.render(page_props, MediaType.JSON, get_serializer(type_encoders)).decode()
        return {
            **self.context,
            "inertia": inertia_props,
            "js_routes": js_routes_script(request.app.state.js_routes),
            "request": request,
            "csrf_input": f'<input type="hidden" name="_csrf_token" value="{csrf_token}" />',
        }

    def to_asgi_response(
        self,
        app: Litestar | None,
        request: Request[UserT, AuthT, StateT],
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        type_encoders: TypeEncodersMap | None = None,
    ) -> ASGIResponse:
        if app is not None:
            warn_deprecation(
                version="2.1",
                deprecated_name="app",
                kind="parameter",
                removal_in="3.0.0",
                alternative="request.app",
            )
        inertia_enabled = getattr(request, "inertia_enabled", False) or getattr(request, "is_inertia", False)
        is_inertia = getattr(request, "is_inertia", False)

        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)
        type_encoders = (
            {**type_encoders, **(self.response_type_encoders or {})} if type_encoders else self.response_type_encoders
        )
        if not inertia_enabled:
            media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            return ASGIResponse(
                background=self.background or background,
                body=self.render(self.content, media_type, get_serializer(type_encoders)),
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=media_type,
                status_code=self.status_code or status_code,
            )
        vite_plugin = request.app.plugins.get(VitePlugin)
        template_engine = vite_plugin.template_config.to_engine()
        headers.update(
            {"Vary": "Accept", **get_headers(InertiaHeaderType(enabled=True))},
        )
        shared_props = get_shared_props(request)
        page_props = PageProps[T](
            component=request.inertia.route_component,  # type: ignore[attr-defined] # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType,reportAttributeAccessIssue]
            props={"content": self.content, **shared_props},  # pyright: ignore[reportArgumentType]
            version=template_engine.asset_loader.version_id,
            url=request.url.path,
        )
        if is_inertia:
            media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            body = self.render(page_props, media_type, get_serializer(type_encoders))
            return ASGIResponse(
                background=self.background or background,
                body=body,
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=media_type,
                status_code=self.status_code or status_code,
            )

        if not template_engine:
            msg = "Template engine is not configured"
            raise ImproperlyConfiguredException(msg)
        # it should default to HTML at this point unless the user specified something
        media_type = media_type or MediaType.HTML
        if not media_type:
            if self.template_name:
                suffixes = PurePath(self.template_name).suffixes
                for suffix in suffixes:
                    if _type := guess_type(f"name{suffix}")[0]:
                        media_type = _type
                        break
                else:
                    media_type = MediaType.TEXT
            else:
                media_type = MediaType.HTML
        context = self.create_template_context(request, page_props, type_encoders)  # pyright: ignore[reportUnknownMemberType]
        if self.template_str is not None:
            body = template_engine.render_string(self.template_str, context).encode(self.encoding)
        else:
            inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
            template_name = self.template_name or inertia_plugin.config.root_template
            # cast to str b/c we know that either template_name cannot be None if template_str is None
            template = template_engine.get_template(template_name)
            body = template.render(**context).encode(self.encoding)

        return ASGIResponse(
            background=self.background or background,
            body=body,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )


class InertiaExternalRedirect(Response[Any]):
    """Client side redirect."""

    def __init__(
        self,
        request: Request[Any, Any, Any],
        redirect_to: str,
        **kwargs: Any,
    ) -> None:
        """Initialize external redirect, Set status code to 409 (required by Inertia),
        and pass redirect url.
        """
        super().__init__(
            content=kwargs.get("content", ""),
            status_code=HTTP_409_CONFLICT,
            headers={"X-Inertia": "true", "X-Inertia-Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
            cookies=request.cookies,
            **kwargs,
        )


class InertiaRedirect(Redirect):
    """Client side redirect."""

    def __init__(
        self,
        request: Request[Any, Any, Any],
        redirect_to: str,
        **kwargs: Any,
    ) -> None:
        """Initialize external redirect, Set status code to 409 (required by Inertia),
        and pass redirect url.
        """
        super().__init__(
            path=redirect_to,
            status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
            cookies=request.cookies,
            **kwargs,
        )


class InertiaBack(Redirect):
    """Client side redirect."""

    def __init__(
        self,
        request: Request[Any, Any, Any],
        **kwargs: Any,
    ) -> None:
        """Initialize external redirect, Set status code to 409 (required by Inertia),
        and pass redirect url.
        """
        referer = request.headers.get("referer", str(request.base_url))
        inertia_enabled = getattr(request, "inertia_enabled", False) or getattr(request, "is_inertia", False)
        if inertia_enabled:
            referer = cast("InertiaRequest[Any, Any, Any]", request).inertia.referer or referer
        super().__init__(
            path=request.headers.get("referer", str(request.base_url)),
            status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
            cookies=request.cookies,
            **kwargs,
        )
