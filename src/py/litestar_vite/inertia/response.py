import contextlib
import itertools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, TypeVar, cast
from urllib.parse import quote, urlparse

import httpx
from litestar import Litestar, MediaType, Request, Response
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response import Redirect
from litestar.response.base import ASGIResponse
from litestar.serialization import get_serializer
from litestar.status_codes import HTTP_200_OK, HTTP_303_SEE_OTHER, HTTP_307_TEMPORARY_REDIRECT, HTTP_409_CONFLICT
from litestar.utils.empty import value_or_default
from litestar.utils.helpers import get_enum_string_value
from litestar.utils.scope.state import ScopeState

from litestar_vite.html_transform import inject_head_html, set_element_inner_html
from litestar_vite.inertia._utils import get_headers
from litestar_vite.inertia.helpers import (
    extract_deferred_props,
    extract_merge_props,
    extract_once_props,
    extract_pagination_scroll_props,
    get_shared_props,
    is_merge_prop,
    is_or_contains_lazy_prop,
    is_or_contains_special_prop,
    is_pagination_container,
    lazy_render,
    pagination_to_dict,
    should_render,
)
from litestar_vite.inertia.plugin import InertiaPlugin
from litestar_vite.inertia.request import InertiaDetails, InertiaRequest
from litestar_vite.inertia.types import InertiaHeaderType, PageProps, ScrollPropsConfig
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from anyio.from_thread import BlockingPortal
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection.base import AuthT, StateT, UserT
    from litestar.types import ResponseCookies, ResponseHeaders, TypeEncodersMap


T = TypeVar("T")


@dataclass(frozen=True)
class _InertiaSSRResult:
    head: list[str]
    body: str


@dataclass(frozen=True)
class _InertiaRequestInfo:
    inertia_enabled: bool
    is_inertia: bool
    is_partial_render: bool
    partial_keys: set[str]
    partial_except_keys: set[str]
    reset_keys: set[str]


def _get_inertia_request_info(request: "Request[Any, Any, Any]") -> _InertiaRequestInfo:
    """Return Inertia request state for both InertiaRequest and plain Request.

    InertiaResponse is typically used together with InertiaMiddleware, which wraps
    incoming requests in :class:`~litestar_vite.inertia.request.InertiaRequest`.

    This helper preserves compatibility with plain :class:`litestar.Request` by
    falling back to header parsing via :class:`~litestar_vite.inertia.request.InertiaDetails`.

    Returns:
        Aggregated Inertia-related request flags and partial-render metadata.
    """
    if isinstance(request, InertiaRequest):
        is_inertia = request.is_inertia
        return _InertiaRequestInfo(
            inertia_enabled=bool(request.inertia_enabled or is_inertia),
            is_inertia=is_inertia,
            is_partial_render=request.is_partial_render,
            partial_keys=request.partial_keys,
            partial_except_keys=request.partial_except_keys,
            reset_keys=request.reset_keys,
        )

    details = InertiaDetails(request)
    is_inertia = bool(details)
    return _InertiaRequestInfo(
        inertia_enabled=bool(details.route_component is not None or is_inertia),
        is_inertia=is_inertia,
        is_partial_render=details.is_partial_render,
        partial_keys=set(details.partial_keys),
        partial_except_keys=set(details.partial_except_keys),
        reset_keys=set(details.reset_keys),
    )


def _parse_inertia_ssr_payload(payload: Any, url: str) -> _InertiaSSRResult:
    if not isinstance(payload, dict):
        msg = f"Inertia SSR server at {url!r} returned unexpected payload type: {type(payload)!r}."
        raise ImproperlyConfiguredException(msg)

    payload_dict = cast("dict[str, Any]", payload)

    body = payload_dict.get("body")
    if not isinstance(body, str):
        msg = f"Inertia SSR server at {url!r} returned invalid 'body' (expected string)."
        raise ImproperlyConfiguredException(msg)

    head_raw: Any = payload_dict.get("head", [])
    if head_raw is None:
        head_raw = []
    if not isinstance(head_raw, list):
        msg = f"Inertia SSR server at {url!r} returned invalid 'head' (expected list[str])."
        raise ImproperlyConfiguredException(msg)

    head_list = cast("list[Any]", head_raw)
    if any(not isinstance(item, str) for item in head_list):
        msg = f"Inertia SSR server at {url!r} returned invalid 'head' (expected list[str])."
        raise ImproperlyConfiguredException(msg)

    return _InertiaSSRResult(head=cast("list[str]", head_list), body=body)


def _render_inertia_ssr_sync(
    page: dict[str, Any],
    url: str,
    *,
    timeout_seconds: float,
    portal: "BlockingPortal",
    client: "httpx.AsyncClient | None" = None,
) -> _InertiaSSRResult:
    """Call the Inertia SSR server and return head/body HTML.

    The official Inertia SSR server listens on ``/render`` and expects the raw
    page object as JSON. It returns JSON with at least a ``body`` field, and
    optionally ``head`` (list of strings).

    This function uses the application's :class:`~anyio.from_thread.BlockingPortal`
    to call the async HTTP client without blocking the event loop thread.

    Args:
        page: The page object to send to the SSR server.
        url: The SSR server URL.
        timeout_seconds: Request timeout in seconds.
        portal: BlockingPortal for sync-to-async bridging.
        client: Optional shared httpx.AsyncClient for connection pooling.

    Returns:
        An _InertiaSSRResult with head and body HTML.
    """
    return portal.call(_render_inertia_ssr, page, url, timeout_seconds, client)


async def _render_inertia_ssr(
    page: dict[str, Any], url: str, timeout_seconds: float, client: "httpx.AsyncClient | None" = None
) -> _InertiaSSRResult:
    """Call the Inertia SSR server asynchronously and return head/body HTML.

    Args:
        page: The page object to send to the SSR server.
        url: The SSR server URL (typically http://localhost:13714/render).
        timeout_seconds: Request timeout in seconds.
        client: Optional shared httpx.AsyncClient for connection pooling.
            If None, creates a new client per request (slower).

    Returns:
        An _InertiaSSRResult with head and body HTML.
    """
    return await _do_ssr_request(page, url, timeout_seconds, client)


async def _do_ssr_request(
    page: dict[str, Any], url: str, timeout_seconds: float, client: "httpx.AsyncClient | None"
) -> _InertiaSSRResult:
    """Execute the SSR request with optional client reuse.

    Args:
        page: The page object to send to the SSR server.
        url: The SSR server URL.
        timeout_seconds: Request timeout in seconds.
        client: Optional shared httpx.AsyncClient.

    Raises:
        ImproperlyConfiguredException: If the SSR server is unreachable,
            returns an error status, or returns invalid payload.

    Returns:
        An _InertiaSSRResult with head and body HTML.
    """
    response: "httpx.Response"

    if client is not None:
        # Use shared client for connection pooling benefits
        try:
            response = await client.post(url, json=page, timeout=timeout_seconds)
            response.raise_for_status()
        except httpx.RequestError as exc:
            msg = (
                f"Inertia SSR is enabled but the SSR server is not reachable at {url!r}. "
                "Start the SSR server (Node) or disable InertiaConfig.ssr."
            )
            raise ImproperlyConfiguredException(msg) from exc
        except httpx.HTTPStatusError as exc:
            msg = f"Inertia SSR server at {url!r} returned HTTP {exc.response.status_code}. Check the SSR server logs."
            raise ImproperlyConfiguredException(msg) from exc
    else:
        # Fallback: create a new client per request (graceful degradation)
        try:
            async with httpx.AsyncClient() as fallback_client:
                response = await fallback_client.post(url, json=page, timeout=timeout_seconds)
                response.raise_for_status()
        except httpx.RequestError as exc:
            msg = (
                f"Inertia SSR is enabled but the SSR server is not reachable at {url!r}. "
                "Start the SSR server (Node) or disable InertiaConfig.ssr."
            )
            raise ImproperlyConfiguredException(msg) from exc
        except httpx.HTTPStatusError as exc:
            msg = f"Inertia SSR server at {url!r} returned HTTP {exc.response.status_code}. Check the SSR server logs."
            raise ImproperlyConfiguredException(msg) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        msg = f"Inertia SSR server at {url!r} returned invalid JSON. Check the SSR server logs."
        raise ImproperlyConfiguredException(msg) from exc

    return _parse_inertia_ssr_payload(payload, url)


def _get_redirect_url(request: "Request[Any, Any, Any]", url: str | None) -> str:
    """Return a safe redirect URL, falling back to base_url when invalid.

    Args:
        request: The request object.
        url: Candidate redirect URL.

    Returns:
        A safe redirect URL (same-origin absolute, or relative), otherwise the request base URL.
    """
    base_url = str(request.base_url)

    if not url:
        return base_url

    parsed = urlparse(url)
    base = urlparse(base_url)

    if not parsed.scheme and not parsed.netloc:
        return url

    if parsed.scheme not in {"http", "https"}:
        return base_url

    if parsed.netloc != base.netloc:
        return base_url

    return url


def _get_relative_url(request: "Request[Any, Any, Any]") -> str:
    """Return the relative URL including query string for Inertia page props.

    The Inertia.js protocol requires the ``url`` property to include query parameters
    so that page state (e.g., filters, pagination) is preserved on refresh.

    This matches the behavior of other Inertia adapters:
    - Laravel: Uses ``fullUrl()`` minus scheme/host
    - Rails: Uses ``request.fullpath``
    - Django: Uses ``request.get_full_path()``

    Args:
        request: The request object.

    Returns:
        The path with query string if present, e.g., ``/reports?page=1&status=active``.
    """
    path = request.url.path
    query = request.url.query
    return f"{path}?{query}" if query else path


class InertiaResponse(Response[T]):
    """Inertia Response"""

    def __init__(
        self,
        content: T,
        *,
        template_name: "str | None" = None,
        template_str: "str | None" = None,
        background: "BackgroundTask | BackgroundTasks | None" = None,
        context: "dict[str, Any] | None" = None,
        cookies: "ResponseCookies | None" = None,
        encoding: "str" = "utf-8",
        headers: "ResponseHeaders | None" = None,
        media_type: "MediaType | str | None" = None,
        status_code: "int" = HTTP_200_OK,
        type_encoders: "TypeEncodersMap | None" = None,
        encrypt_history: "bool | None" = None,
        clear_history: bool = False,
        scroll_props: "ScrollPropsConfig | None" = None,
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
            encrypt_history: Enable browser history encryption for this response (v2 feature).
                When True, the Inertia client encrypts history state using the browser's
                crypto API. If None, falls back to InertiaConfig.encrypt_history.
                See: https://inertiajs.com/history-encryption
            clear_history: Clear previously encrypted history state (v2 feature).
                When True, the client will regenerate its encryption key, invalidating
                all previously encrypted history entries. Use during logout to ensure
                sensitive data cannot be recovered from browser history.
            scroll_props: Configuration for infinite scroll (v2 feature).
                Provides next/previous page information for paginated data.
                Use the scroll_props() helper to create this configuration.

        Raises:
            ValueError: If both template_name and template_str are provided.
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
        self.encrypt_history = encrypt_history
        self.clear_history = clear_history
        self.scroll_props = scroll_props

    def create_template_context(
        self,
        request: "Request[UserT, AuthT, StateT]",
        page_props: "PageProps[T]",
        type_encoders: "TypeEncodersMap | None" = None,
    ) -> "dict[str, Any]":
        """Create a context object for the template.

        Args:
            request: A :class:`Request <.connection.Request>` instance.
            page_props: A formatted object to return the inertia configuration.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.

        Returns:
            A dictionary holding the template context
        """
        csrf_token = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
        inertia_props = self.render(page_props.to_dict(), MediaType.JSON, get_serializer(type_encoders)).decode()
        return {
            **self.context,
            "inertia": inertia_props,
            "request": request,
            "csrf_input": f'<input type="hidden" name="_csrf_token" value="{csrf_token}" />',
        }

    def _build_page_props(
        self,
        request: "Request[UserT, AuthT, StateT]",
        partial_data: "set[str] | None",
        partial_except: "set[str] | None",
        reset_keys: "set[str]",
        vite_plugin: "VitePlugin",
        inertia_plugin: "InertiaPlugin",
    ) -> "PageProps[T]":
        """Build the PageProps object for the response.

        Args:
            request: The request object.
            partial_data: Set of partial data keys.
            partial_except: Set of partial except keys.
            reset_keys: Set of keys to reset.
            vite_plugin: The Vite plugin instance.
            inertia_plugin: The Inertia plugin instance.

        Returns:
            The PageProps object.
        """
        shared_props = get_shared_props(request, partial_data=partial_data, partial_except=partial_except)

        for key in reset_keys:
            shared_props.pop(key, None)

        route_content: Any | None = None
        if is_or_contains_lazy_prop(self.content) or is_or_contains_special_prop(self.content):
            filtered_content = lazy_render(self.content, partial_data, inertia_plugin.portal, partial_except)
            if filtered_content is not None:
                route_content = filtered_content
        elif should_render(self.content, partial_data, partial_except):
            route_content = self.content

        if route_content is not None:
            if isinstance(route_content, Mapping):
                mapping_content = cast("Mapping[str, Any]", route_content)
                for key, value in mapping_content.items():
                    shared_props[key] = value
            elif is_pagination_container(route_content):
                route_handler = request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
                prop_key = (route_handler.opt.get("key", "items") if route_handler else "items") or "items"
                shared_props[prop_key] = route_content
            else:
                shared_props["content"] = route_content

        deferred_props = extract_deferred_props(shared_props) or None
        # Extract once props tracked during get_shared_props (already rendered)
        once_props_from_shared = shared_props.pop("_once_props", [])
        # Also check route content for once props
        once_props_from_content = extract_once_props(shared_props) or []
        once_props = (once_props_from_shared + once_props_from_content) or None

        merge_props_list, prepend_props_list, deep_merge_props_list, match_props_on = extract_merge_props(shared_props)

        for key, value in list(shared_props.items()):
            if is_merge_prop(value):
                shared_props[key] = value.value

        extracted_scroll_props: "ScrollPropsConfig | None" = self.scroll_props

        route_handler = request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
        infinite_scroll_enabled = bool(route_handler and route_handler.opt.get("infinite_scroll", False))

        for key, value in list(shared_props.items()):
            if is_pagination_container(value):
                _, scroll = extract_pagination_scroll_props(value)
                if extracted_scroll_props is None and scroll is not None and infinite_scroll_enabled:
                    extracted_scroll_props = scroll

                pagination_dict = pagination_to_dict(value)
                shared_props[key] = pagination_dict.pop("items")
                shared_props.update(pagination_dict)

        encrypt_history = self.encrypt_history
        if encrypt_history is None:
            encrypt_history = inertia_plugin.config.encrypt_history

        clear_history_flag = self.clear_history
        if not clear_history_flag:
            with contextlib.suppress(AttributeError, ImproperlyConfiguredException):
                clear_history_flag = request.session.pop("_inertia_clear_history", False)  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

        # v2.3+ protocol: Extract flash to top level (not in props)
        # This prevents flash from persisting in browser history state
        # Always send {} for empty flash to support router.flash((current) => ({ ...current }))
        flash_data: "dict[str, list[str]]" = shared_props.pop("flash", None) or {}

        return PageProps[T](
            component=request.inertia.route_component,  # type: ignore[attr-defined] # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType,reportAttributeAccessIssue]
            props=shared_props,  # pyright: ignore[reportArgumentType]
            version=vite_plugin.asset_loader.version_id,
            url=_get_relative_url(request),
            encrypt_history=encrypt_history,
            clear_history=clear_history_flag,
            deferred_props=deferred_props,
            once_props=once_props,
            merge_props=merge_props_list or None,
            prepend_props=prepend_props_list or None,
            deep_merge_props=deep_merge_props_list or None,
            match_props_on=match_props_on or None,
            scroll_props=extracted_scroll_props,
            flash=flash_data,
        )

    def _render_template(
        self,
        request: "Request[UserT, AuthT, StateT]",
        page_props: "PageProps[T]",
        type_encoders: "TypeEncodersMap | None",
        inertia_plugin: "InertiaPlugin",
    ) -> bytes:
        """Render the template to bytes.

        Args:
            request: The request object.
            page_props: The page props to render.
            type_encoders: Type encoders for serialization.
            inertia_plugin: The Inertia plugin instance.

        Returns:
            The rendered template as bytes.

        Raises:
            ImproperlyConfiguredException: If the template engine is not configured.
        """
        template_engine = request.app.template_engine  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if not template_engine:
            msg = "Template engine is not configured"
            raise ImproperlyConfiguredException(msg)

        context = self.create_template_context(request, page_props, type_encoders)  # pyright: ignore[reportUnknownMemberType]
        if self.template_str is not None:
            return template_engine.render_string(self.template_str, context).encode(self.encoding)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType,reportReturnType]

        template_name = self.template_name or inertia_plugin.config.root_template
        template = template_engine.get_template(template_name)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        return template.render(**context).encode(self.encoding)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType,reportReturnType]

    def _get_csrf_token(self, request: "Request[UserT, AuthT, StateT]") -> "str | None":
        """Extract CSRF token from the request scope.

        Args:
            request: The incoming request.

        Returns:
            The CSRF token if available, otherwise None.
        """
        csrf_token = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
        return csrf_token or None

    def _render_spa(
        self,
        request: "Request[UserT, AuthT, StateT]",
        page_props: "PageProps[T]",
        vite_plugin: "VitePlugin",
        inertia_plugin: "InertiaPlugin",
    ) -> bytes:
        """Render the page using SPA mode (HTML transformation instead of templates).

        This method uses AppHandler to get the base HTML and injects
        the page props as a data-page attribute on the app element.

        Uses get_html_sync() for both dev and production modes to avoid
        deadlocks when calling async code from sync context within the
        same event loop thread.

        Args:
            request: The request object.
            page_props: The page props to render.
            vite_plugin: The Vite plugin instance (for SPA handler access).
            inertia_plugin: The Inertia plugin instance (for config access).

        Returns:
            The rendered HTML as bytes.

        Raises:
            ImproperlyConfiguredException: If AppHandler is not available.
        """
        spa_handler = vite_plugin.spa_handler
        if spa_handler is None:
            msg = (
                "SPA mode requires VitePlugin with mode='spa' or mode='hybrid'. "
                "Set mode='hybrid' in ViteConfig for template-less Inertia."
            )
            raise ImproperlyConfiguredException(msg)

        page_dict = page_props.to_dict()

        ssr_config = inertia_plugin.config.ssr_config
        if ssr_config is not None:
            ssr_payload = _render_inertia_ssr_sync(
                page_dict,
                ssr_config.url,
                timeout_seconds=ssr_config.timeout,
                portal=inertia_plugin.portal,
                client=inertia_plugin.ssr_client,
            )

            csrf_token = self._get_csrf_token(request)
            html = spa_handler.get_html_sync(page_data=page_dict, csrf_token=csrf_token)

            selector = "#app"
            spa_config = spa_handler._spa_config  # pyright: ignore
            if spa_config is not None:
                selector = spa_config.app_selector

            html = set_element_inner_html(html, selector, ssr_payload.body)
            if ssr_payload.head:
                html = inject_head_html(html, "\n".join(ssr_payload.head))

            return html.encode(self.encoding)

        csrf_token = self._get_csrf_token(request)

        html = spa_handler.get_html_sync(page_data=page_dict, csrf_token=csrf_token)

        return html.encode(self.encoding)

    def _determine_media_type(self, media_type: "MediaType | str | None") -> "MediaType | str":
        """Determine the media type for the response.

        Args:
            media_type: The provided media type or None.

        Returns:
            The determined media type.
        """
        if media_type:
            return media_type
        if self.template_name:
            suffixes = PurePath(self.template_name).suffixes
            for suffix in suffixes:
                if type_ := guess_type(f"name{suffix}")[0]:
                    return type_
            return MediaType.TEXT
        return MediaType.HTML

    def to_asgi_response(
        self,
        app: "Litestar | None",
        request: "Request[UserT, AuthT, StateT]",
        *,
        background: "BackgroundTask | BackgroundTasks | None" = None,
        cookies: "Iterable[Cookie] | None" = None,
        encoded_headers: "Iterable[tuple[bytes, bytes]] | None" = None,
        headers: "dict[str, str] | None" = None,
        is_head_response: "bool" = False,
        media_type: "MediaType | str | None" = None,
        status_code: "int | None" = None,
        type_encoders: "TypeEncodersMap | None" = None,
    ) -> "ASGIResponse":
        inertia_info = _get_inertia_request_info(cast("Request[Any, Any, Any]", request))
        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)
        type_encoders = (
            {**type_encoders, **(self.response_type_encoders or {})} if type_encoders else self.response_type_encoders
        )

        if not inertia_info.inertia_enabled:
            resolved_media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            return ASGIResponse(
                background=self.background or background,
                body=self.render(self.content, resolved_media_type, get_serializer(type_encoders)),
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=resolved_media_type,
                status_code=self.status_code or status_code,
            )

        vite_plugin = request.app.plugins.get(VitePlugin)
        inertia_plugin = request.app.plugins.get(InertiaPlugin)
        headers.update({
            "Vary": "Accept",
            **get_headers(InertiaHeaderType(enabled=True, version=vite_plugin.asset_loader.version_id)),
        })

        partial_data: "set[str] | None" = (
            inertia_info.partial_keys if inertia_info.is_partial_render and inertia_info.partial_keys else None
        )
        partial_except: "set[str] | None" = (
            inertia_info.partial_except_keys
            if inertia_info.is_partial_render and inertia_info.partial_except_keys
            else None
        )

        page_props = self._build_page_props(
            request, partial_data, partial_except, inertia_info.reset_keys, vite_plugin, inertia_plugin
        )

        if inertia_info.is_inertia:
            resolved_media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            body = self.render(page_props.to_dict(), resolved_media_type, get_serializer(type_encoders))
            return ASGIResponse(  # pyright: ignore[reportUnknownMemberType]
                background=self.background or background,
                body=body,
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=resolved_media_type,
                status_code=self.status_code or status_code,
            )

        resolved_media_type = self._determine_media_type(media_type or MediaType.HTML)

        if vite_plugin.config.mode == "hybrid":
            body = self._render_spa(request, page_props, vite_plugin, inertia_plugin)
        else:
            body = self._render_template(request, page_props, type_encoders, inertia_plugin)

        return ASGIResponse(  # pyright: ignore[reportUnknownMemberType]
            background=self.background or background,
            body=body,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=resolved_media_type,
            status_code=self.status_code or status_code,
        )


class InertiaExternalRedirect(Response[Any]):
    """External redirect via Inertia protocol (409 + X-Inertia-Location).

    This response type triggers a client-side hard redirect in Inertia.js.
    Unlike InertiaRedirect, this does NOT validate the redirect URL as same-origin
    because external redirects are explicitly intended for cross-origin navigation
    (e.g., OAuth callbacks, external payment pages).

    Note:
        Request cookies are intentionally NOT passed to the response to prevent
        cookie leakage in redirect responses.
    """

    def __init__(self, request: "Request[Any, Any, Any]", redirect_to: "str", **kwargs: "Any") -> None:
        """Initialize external redirect with 409 status and X-Inertia-Location header.

        Args:
            request: The request object.
            redirect_to: The URL to redirect to (can be external).
            **kwargs: Additional keyword arguments passed to the Response constructor.
        """
        super().__init__(
            content=b"",
            status_code=HTTP_409_CONFLICT,
            headers={"X-Inertia-Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
            **kwargs,
        )


class InertiaRedirect(Redirect):
    """Redirect to a specified URL with same-origin validation.

    This class validates the redirect URL to prevent open redirect attacks.
    If the URL is not same-origin, it falls back to the application's base URL.

    Note:
        Request cookies are intentionally NOT passed to the response to prevent
        cookie leakage in redirect responses.
    """

    def __init__(self, request: "Request[Any, Any, Any]", redirect_to: "str", **kwargs: "Any") -> None:
        """Initialize redirect with safe URL validation.

        Args:
            request: The request object.
            redirect_to: The URL to redirect to. Must be same-origin or relative.
            **kwargs: Additional keyword arguments passed to the Redirect constructor.
        """
        safe_url = _get_redirect_url(request, redirect_to)
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            path=safe_url,
            status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
            **kwargs,
        )


class InertiaBack(Redirect):
    """Redirect back to the previous page using the Referer header.

    This class safely validates the Referer header to prevent open redirect
    attacks. If the Referer is not same-origin or is missing, it falls back
    to the application's base URL.

    Note:
        Request cookies are intentionally NOT passed to the response to prevent
        cookie leakage in redirect responses.
    """

    def __init__(self, request: "Request[Any, Any, Any]", **kwargs: "Any") -> None:
        """Initialize back redirect with safe URL validation.

        Args:
            request: The request object.
            **kwargs: Additional keyword arguments passed to the Redirect constructor.
        """
        safe_url = _get_redirect_url(request, request.headers.get("Referer"))
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            path=safe_url,
            status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
            **kwargs,
        )
