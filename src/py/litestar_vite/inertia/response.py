from __future__ import annotations

import inspect
import itertools
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager
from functools import lru_cache
from mimetypes import guess_type
from pathlib import PurePath
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    TypeVar,
    cast,
    overload,
)
from urllib.parse import quote, urlparse, urlunparse

from anyio.from_thread import BlockingPortal, start_blocking_portal
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
from typing_extensions import ParamSpec, TypeGuard

from litestar_vite.inertia._utils import get_headers
from litestar_vite.inertia.types import InertiaHeaderType, PageProps
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import ASGIConnection
    from litestar.connection.base import AuthT, StateT, UserT
    from litestar.types import ResponseCookies, ResponseHeaders, TypeEncodersMap

    from litestar_vite.inertia.plugin import InertiaPlugin
    from litestar_vite.inertia.routes import Routes

T = TypeVar("T")
T_ParamSpec = ParamSpec("T_ParamSpec")
PropKeyT = TypeVar("PropKeyT", bound=str)
StaticT = TypeVar("StaticT", bound=object)


@overload
def lazy(key: str, value_or_callable: None) -> StaticProp[str, None]: ...


@overload
def lazy(key: str, value_or_callable: T) -> StaticProp[str, T]: ...


@overload
def lazy(
    key: str,
    value_or_callable: Callable[..., None] = ...,
) -> DeferredProp[str, None]: ...


@overload
def lazy(
    key: str,
    value_or_callable: Callable[T_ParamSpec, T | Coroutine[Any, Any, T]] = ...,  # pyright: ignore[reportInvalidTypeVarUse]
) -> DeferredProp[str, T]: ...


def lazy(  # type: ignore[misc]
    key: str,
    value_or_callable: T | Callable[T_ParamSpec, T | Coroutine[Any, Any, T]],  # pyright: ignore[reportInvalidTypeVarUse]
) -> StaticProp[str, None] | StaticProp[str, T] | DeferredProp[str, T] | DeferredProp[str, None]:
    """Wrap an async function to return a DeferredProp."""
    if value_or_callable is None:
        return StaticProp[str, None](key=key, value=None)

    if not callable(value_or_callable):
        return StaticProp[str, T](key=key, value=value_or_callable)

    return DeferredProp[str, T](key=key, value=value_or_callable)  # pyright: ignore[reportArgumentType]


class StaticProp(Generic[PropKeyT, StaticT]):
    """A wrapper for static property evaluation."""

    def __init__(self, key: PropKeyT, value: StaticT) -> None:
        self._key = key
        self._result = value

    @property
    def key(self) -> PropKeyT:
        return self._key

    def render(self, portal: BlockingPortal | None = None) -> StaticT:
        return self._result


class DeferredProp(Generic[PropKeyT, T]):
    """A wrapper for deferred property evaluation."""

    def __init__(self, key: PropKeyT, value: Callable[T_ParamSpec, T | Coroutine[Any, Any, T]] | None = None) -> None:
        self._key = key
        self._value = value
        self._evaluated = False
        self._result: T | None = None

    @property
    def key(self) -> PropKeyT:
        return self._key

    @staticmethod
    def _is_awaitable(
        v: Callable[T_ParamSpec, T | Coroutine[Any, Any, T]],
    ) -> TypeGuard[Coroutine[Any, Any, T]]:
        return inspect.iscoroutinefunction(v)

    @staticmethod
    @contextmanager
    def _with_portal(portal: BlockingPortal | None = None) -> Generator[BlockingPortal, None, None]:
        if portal is None:
            with start_blocking_portal() as new_portal:
                yield new_portal
        else:
            yield portal

    def render(self, portal: BlockingPortal | None = None) -> T | None:
        if self._evaluated:
            return self._result  # type: ignore
        if self._value is None or not callable(self._value):
            self._result = self._value  # type: ignore
        elif not self._is_awaitable(self._value):
            self._result = self._value()  # type: ignore
        else:
            with self._with_portal(portal) as bp:
                self._result = bp.call(self._value)  # type: ignore[call-overload]
        self._evaluated = True
        return self._result  # type: ignore


def is_lazy_prop(value: Any) -> TypeGuard[DeferredProp[Any, Any]]:
    """Check if value is a deferred property.

    Args:
        value: Any value to check

    Returns:
        bool: True if value is a deferred property
    """
    return isinstance(value, (DeferredProp, StaticProp))


def should_render(value: Any, partial_data: set[str] | None = None) -> bool:
    """Check if value should be rendered.

    Args:
        value: Any value to check
        partial_data: Optional set of keys for partial rendering

    Returns:
        bool: True if value should be rendered
    """
    partial_data = partial_data or set()
    if is_lazy_prop(value):
        return value.key in partial_data
    return True


def is_or_contains_lazy_prop(value: Any) -> bool:
    """Check if value is or contains a deferred property.

    Args:
        value: Any value to check

    Returns:
        bool: True if value is or contains a deferred property
    """
    if is_lazy_prop(value):
        return True
    if isinstance(value, str):
        return False
    if isinstance(value, Mapping):
        return any(is_or_contains_lazy_prop(v) for v in cast("Mapping[str, Any]", value).values())
    if isinstance(value, Iterable):
        return any(is_or_contains_lazy_prop(v) for v in cast("Iterable[Any]", value))
    return False


def lazy_render(value: T, partial_data: set[str] | None = None, portal: BlockingPortal | None = None) -> T:
    """Filter deferred properties from the value based on partial data.

    Args:
        value: The value to filter
        partial_data: Keys for partial rendering
        portal: Optional portal to use for async rendering
    Returns:
        The filtered value
    """
    partial_data = partial_data or set()
    if isinstance(value, str):
        return cast("T", value)
    if isinstance(value, Mapping):
        return cast(
            "T",
            {
                k: lazy_render(v, partial_data)
                for k, v in cast("Mapping[str, Any]", value).items()
                if should_render(v, partial_data)
            },
        )

    if isinstance(value, (list, tuple)):
        filtered = [
            lazy_render(v, partial_data) for v in cast("Iterable[Any]", value) if should_render(v, partial_data)
        ]
        return cast("T", type(value)(filtered))  # pyright: ignore[reportUnknownArgumentType]

    if is_lazy_prop(value) and should_render(value, partial_data):
        return cast("T", value.render())

    return cast("T", value)


def get_shared_props(
    request: ASGIConnection[Any, Any, Any, Any],
    partial_data: set[str] | None = None,
) -> dict[str, Any]:
    """Return shared session props for a request.

    Args:
        request: The ASGI connection.
        partial_data: Optional set of keys for partial rendering.

    Returns:
        Dict[str, Any]: The shared props.

    Note:
        Be sure to call this before `self.create_template_context` if you would like to include the `flash` message details.
    """
    props: dict[str, Any] = {}
    flash: dict[str, list[str]] = defaultdict(list)
    errors: dict[str, Any] = {}
    error_bag = request.headers.get("X-Inertia-Error-Bag", None)

    try:
        errors = request.session.pop("_errors", {})
        shared_props = cast("Dict[str,Any]", request.session.pop("_shared", {}))

        # Handle deferred props
        for key, value in shared_props.items():
            if is_lazy_prop(value) and should_render(value, partial_data):
                props[key] = value.render()
                continue
            if should_render(value, partial_data):
                props[key] = value

        for message in cast("List[Dict[str,Any]]", request.session.pop("_messages", [])):
            flash[message["category"]].append(message["message"])

        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
        props.update(inertia_plugin.config.extra_static_page_props)
        for session_prop in inertia_plugin.config.extra_session_page_props:
            if session_prop not in props and session_prop in request.session:
                props[session_prop] = request.session.get(session_prop)

    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to generate all shared props.  A valid session was not found for this request."
        request.logger.warning(msg)

    props["flash"] = flash
    props["errors"] = {error_bag: errors} if error_bag is not None else errors
    props["csrf_token"] = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
    return props


def share(
    connection: ASGIConnection[Any, Any, Any, Any],
    key: str,
    value: Any,
) -> None:
    """Share a value in the session.

    Args:
        connection: The ASGI connection.
        key: The key to store the value under.
        value: The value to store.
    """
    try:
        connection.session.setdefault("_shared", {}).update({key: value})
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to set `share` session state.  A valid session was not found for this request."
        connection.logger.warning(msg)


def error(
    connection: ASGIConnection[Any, Any, Any, Any],
    key: str,
    message: str,
) -> None:
    """Set an error message in the session.

    Args:
        connection: The ASGI connection.
        key: The key to store the error under.
        message: The error message.
    """
    try:
        connection.session.setdefault("_errors", {}).update({key: message})
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to set `error` session state.  A valid session was not found for this request."
        connection.logger.warning(msg)


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

    def to_asgi_response(  # noqa: C901, PLR0912
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
        inertia_enabled = cast(
            "bool",
            getattr(request, "inertia_enabled", False) or getattr(request, "is_inertia", False),
        )
        is_inertia = cast("bool", getattr(request, "is_inertia", False))
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
        is_partial_render = cast("bool", getattr(request, "is_partial_render", False))
        partial_keys = cast("set[str]", getattr(request, "partial_keys", {}))
        vite_plugin = request.app.plugins.get(VitePlugin)
        template_engine = request.app.template_engine  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        headers.update(
            {"Vary": "Accept", **get_headers(InertiaHeaderType(enabled=True))},
        )
        shared_props = get_shared_props(request, partial_data=partial_keys if is_partial_render else None)
        if is_or_contains_lazy_prop(self.content):
            filtered_content = lazy_render(self.content, partial_keys if is_partial_render else None)
            if filtered_content is not None:
                shared_props["content"] = filtered_content
        elif should_render(self.content, partial_keys):
            shared_props["content"] = self.content

        page_props = PageProps[T](
            component=request.inertia.route_component,  # type: ignore[attr-defined] # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType,reportAttributeAccessIssue]
            props=shared_props,  # pyright: ignore[reportArgumentType]
            version=vite_plugin.asset_loader.version_id,
            url=request.url.path,
        )
        if is_inertia:
            media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            body = self.render(page_props, media_type, get_serializer(type_encoders))
            return ASGIResponse(  # pyright: ignore[reportUnknownMemberType]
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
            body = template_engine.render_string(self.template_str, context).encode(self.encoding)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        else:
            inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
            template_name = self.template_name or inertia_plugin.config.root_template
            template = template_engine.get_template(template_name)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            body = template.render(**context).encode(self.encoding)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]

        return ASGIResponse(  # pyright: ignore[reportUnknownMemberType]
            background=self.background or background,
            body=body,  # pyright: ignore[reportUnknownArgumentType]
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
            content=b"",
            status_code=HTTP_409_CONFLICT,
            headers={"X-Inertia-Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
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
        referer = urlparse(request.headers.get("Referer", str(request.base_url)))
        redirect_to = urlunparse(urlparse(redirect_to)._replace(scheme=referer.scheme))
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
        super().__init__(
            path=request.headers.get("Referer", str(request.base_url)),
            status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
            cookies=request.cookies,
            **kwargs,
        )
