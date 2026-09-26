import contextlib
import itertools
import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast
from urllib.parse import quote, urlparse

from litestar import Litestar, MediaType, Request, Response
from litestar.datastructures.cookie import Cookie
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response import Redirect
from litestar.response.base import ASGIResponse
from litestar.serialization import decode_json, encode_json, get_serializer
from litestar.status_codes import HTTP_200_OK, HTTP_303_SEE_OTHER, HTTP_307_TEMPORARY_REDIRECT, HTTP_409_CONFLICT
from litestar.utils.empty import value_or_default
from litestar.utils.helpers import get_enum_string_value
from litestar.utils.scope.state import ScopeState

from litestar_vite.html_transform import inject_inertia_ssr_tags
from litestar_vite.inertia._utils import InertiaHeaders, get_headers
from litestar_vite.inertia.helpers import (
    PropFilter,
    _extract_once_prop_entries,  # pyright: ignore[reportPrivateUsage]
    build_once_props_metadata,
    extract_deferred_props,
    extract_merge_props,
    extract_pagination_scroll_props,
    get_raw_shared_props,
    get_shared_props,
    has_unresolved_async_props,
    is_or_contains_special_prop,
    is_pagination_container,
    lazy_render,
    pagination_to_dict,
    resolve_async_props,
    should_render,
    unwrap_merge_props,
)
from litestar_vite.inertia.plugin import InertiaPlugin
from litestar_vite.inertia.request import InertiaDetails, InertiaRequest
from litestar_vite.inertia.state import consume_clear_history, persist_transient_state_for_redirect
from litestar_vite.inertia.types import InertiaHeaderType, PageProps, ScrollPropsConfig
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection.base import AuthT, StateT, UserT
    from litestar.types import ResponseCookies, ResponseHeaders, TypeEncodersMap

    from litestar_vite.ipc import BaseIPCTransport

logger = logging.getLogger("litestar_vite.inertia")
_INERTIA_PAGE_SCRIPT_PATTERN = re.compile(r"<script[^>]+(?:data-page=|id=[\"']app_page[\"'])", re.IGNORECASE)

T = TypeVar("T")


class InertiaResponse(Response[T]):
    """Inertia Response"""

    def __init__(
        self,
        content: T,
        *,
        template_name: "str | None" = None,
        template_str: "str | None" = None,
        component: "str | None" = None,
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
        prop_filter: "PropFilter | None" = None,
    ) -> None:
        """Handle the rendering of a given template into a bytes string.

        Args:
            content: A value for the response body that will be rendered into bytes string.
            template_name: Path-like name for the template to be rendered, e.g. ``index.html``.
            template_str: A string representing the template, e.g. ``tmpl = "Hello <strong>World</strong>"``.
            component: The Inertia page component name. When omitted, the component
                registered on the route handler (``request.inertia.route_component``) is used.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to ``None``.
            context: A dictionary of key/value pairs to be passed to the temple engine's render method.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: Content encoding
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            media_type: A string or member of the :class:`MediaType <.enums.MediaType>` enum. If not set, Inertia JSON
                responses use ``application/json`` and HTML bootstrap responses use ``text/html``.
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
            prop_filter: Optional route-prop filter created with ``only()`` or
                ``except_()``. Filters this response's route content keys only.

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
        self.prop_filter = prop_filter
        self.component = component
        self._async_prepass_done: bool = False
        self._cached_page_props: "PageProps[T] | None" = None
        self._cached_ssr_payload: "_InertiaSSRResult | None" = None
        self._defer_status_to_handler: bool = False

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
        is_partial_render: bool,
        except_once_props: "set[str] | None",
        reset_keys: "set[str]",
        vite_plugin: "VitePlugin",
        inertia_plugin: "InertiaPlugin",
    ) -> "PageProps[T]":
        """Build the PageProps object for the response.

        Args:
            request: The request object.
            partial_data: Set of partial data keys.
            partial_except: Set of partial except keys.
            is_partial_render: Whether this response is for an Inertia partial reload.
            except_once_props: Set of cached once-prop keys sent by the client.
            reset_keys: Set of keys to reset.
            vite_plugin: The Vite plugin instance.
            inertia_plugin: The Inertia plugin instance.

        Returns:
            The PageProps object.
        """
        raw_shared_props = get_raw_shared_props(request)
        deferred_props_map: "dict[str, list[str]]" = {}
        _merge_deferred_props(deferred_props_map, extract_deferred_props(raw_shared_props))

        shared_props = get_shared_props(
            request, partial_data=partial_data, partial_except=partial_except, except_once_props=except_once_props
        )

        for key in reset_keys:
            shared_props.pop(key, None)

        route_handler = request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
        content: Any = self.content
        route_content: Any | None = None
        route_once_props: "list[tuple[str, str]]" = []
        route_prop_keys: list[str] = []

        if isinstance(content, Mapping):
            content_mapping = cast("Mapping[str, Any]", content)
            for key in content_mapping:
                _discard_deferred_prop_key(deferred_props_map, str(key))
            _merge_deferred_props(deferred_props_map, extract_deferred_props(content_mapping))
            route_once_props = _extract_once_prop_entries(
                content_mapping, partial_data=partial_data, partial_except=partial_except
            )

        if is_or_contains_special_prop(content):
            filtered_content: Any = lazy_render(cast("Any", content), partial_data, partial_except, except_once_props)
            if filtered_content is not None:
                route_content = filtered_content
        elif isinstance(content, Mapping) and (partial_data or partial_except):
            route_content = lazy_render(
                cast("Mapping[str, Any]", content), partial_data, partial_except, except_once_props
            )
        elif should_render(content, partial_data, partial_except, except_once_props):
            route_content = cast("Any", content)

        if route_content is not None:
            if isinstance(route_content, Mapping):
                mapping_content = cast("Mapping[str, Any]", route_content)
                for key, value in mapping_content.items():
                    if self.prop_filter is not None and not self.prop_filter.should_include(str(key)):
                        continue
                    shared_props[key] = value
                    route_prop_keys.append(str(key))
            elif is_pagination_container(route_content):
                prop_key = _get_route_prop_key(route_handler)
                shared_props[prop_key] = route_content
                route_prop_keys.append(prop_key)
            else:
                shared_props["content"] = route_content
                route_prop_keys.append("content")

        deferred_props = _resolve_deferred_props(deferred_props_map, is_partial_render)
        once_props_from_shared = shared_props.pop("_once_props", [])
        once_prop_entries = _dedupe_once_prop_entries(
            [*once_props_from_shared, *route_once_props], reset_keys=reset_keys
        )
        once_props = build_once_props_metadata(once_prop_entries) or None

        merge_props_list, prepend_props_list, deep_merge_props_list, match_props_on = extract_merge_props(shared_props)
        if merge_props_list or prepend_props_list or deep_merge_props_list or match_props_on:
            shared_props = unwrap_merge_props(shared_props)

        scroll_props = _apply_pagination_props(
            shared_props,
            route_handler=route_handler,
            explicit_scroll_props=self.scroll_props,
            explicit_scroll_props_key=_get_explicit_scroll_props_key(route_prop_keys, route_handler),
        )

        encrypt_history = _resolve_encrypt_history(self.encrypt_history, inertia_plugin)
        clear_history_flag = _resolve_clear_history(self.clear_history, request)

        flash_data: "dict[str, list[str]]" = shared_props.pop("flash", None) or {}

        return PageProps[T](
            component=self.component or request.inertia.route_component,  # type: ignore[attr-defined] # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType,reportAttributeAccessIssue]
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
            scroll_props=scroll_props,
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
            html = cast(
                "str",
                template_engine.render_string(self.template_str, context),  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            )
        else:
            template_name = self.template_name or inertia_plugin.config.root_template
            template = template_engine.get_template(template_name)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            html = cast("str", template.render(**context))  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]

        if self._cached_ssr_payload is not None:
            ssr_config = inertia_plugin.config.ssr_config
            selector = ssr_config.target_selector if ssr_config is not None else "#app"
            html = inject_inertia_ssr_tags(
                html, head=self._cached_ssr_payload.head, body=self._cached_ssr_payload.body, selector=selector
            )

        return html.encode(self.encoding)

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
        *,
        ssr: bool = True,
    ) -> bytes:
        """Render the page using SPA mode (HTML transformation instead of templates).

        This method uses AppHandler to get the base HTML and injects
        the page props via page_data (which injects the page script into the document
        when use_script_element is true, or sets data-page on the app element).
        In SSR mode, the page payload is supplied to the shell so the client-side
        bootstrap survives app-element replacement. If the SSR body payload already
        contains an Inertia bootstrap script, passing page data to the shell is omitted
        to prevent duplicate bootstrap tags.

        SSR (when configured) is fetched by the async pre-pass and stored on
        ``self._cached_ssr_payload``; this method just consumes it.

        Args:
            request: The request object.
            page_props: The page props to render.
            vite_plugin: The Vite plugin instance (for SPA handler access).
            ssr: Whether to apply cached SSR markup if available. Defaults to True.

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

        if ssr and self._cached_ssr_payload is not None:
            ssr_payload = self._cached_ssr_payload

            csrf_token = self._get_csrf_token(request)
            page_data = None if _INERTIA_PAGE_SCRIPT_PATTERN.search(ssr_payload.body) else page_dict
            html = spa_handler.get_html_sync(page_data=page_data, csrf_token=csrf_token)

            selector = "#app"
            spa_config = getattr(spa_handler, "_spa_config", None)
            if spa_config is not None:
                selector = getattr(spa_config, "app_selector", selector)

            html = inject_inertia_ssr_tags(html, head=ssr_payload.head, body=ssr_payload.body, selector=selector)

            return html.encode(self.encoding)

        csrf_token = self._get_csrf_token(request)

        html = spa_handler.get_html_sync(page_data=page_dict, csrf_token=csrf_token)

        return html.encode(self.encoding)

    def _will_render_ssr(self, request: "Request[Any, Any, Any]", inertia_info: "_InertiaRequestInfo") -> bool:
        """Predict whether this response will hit the SSR HTTP server.

        Used by the deferral gate in :meth:`to_asgi_response` to decide whether
        async pre-pass is required. Conditions: Inertia is enabled, the request
        is NOT an Inertia JSON request, the plugin has SSR config, and the Vite
        plugin's render path can host the SSR fragment:

        - ``mode='spa'`` / ``mode='hybrid'`` consume ``_cached_ssr_payload`` via ``_render_spa``.
        - ``mode='template'`` consumes ``_cached_ssr_payload`` via ``_render_template``.

        Returns:
            ``True`` if this response will perform an SSR HTTP fetch.
        """
        if not inertia_info.inertia_enabled or inertia_info.is_inertia:
            return False
        try:
            inertia_plugin = request.app.plugins.get(InertiaPlugin)
            vite_plugin = request.app.plugins.get(VitePlugin)
        except KeyError:
            return False
        if inertia_plugin.config.ssr_config is None:
            return False
        return vite_plugin.config.inertia_compatible

    def _determine_media_type(self, media_type: "MediaType | str | None") -> "MediaType | str":
        """Determine the media type for HTML bootstrap responses.

        Args:
            media_type: The provided media type or None.

        Returns:
            The provided media type, or HTML when unset.
        """
        if media_type:
            return media_type
        return MediaType.HTML

    async def resolve_async_props(self, request: "Request[Any, Any, Any]") -> None:
        """Resolve async prop callbacks on the request loop, before DI cleanup.

        Idempotent: returns immediately once ``_async_prepass_done`` is set.

        Should run inside Litestar's ``_call_handler_function`` ``AsyncExitStack``
        frame so any yield-based DI dependencies (sqlspec asyncpg, advanced-alchemy,
        ...) are still alive when prop callbacks await them. The
        :class:`~litestar_vite.inertia.plugin.InertiaPlugin` wraps each route
        handler at app init to call this method automatically; callers normally
        do not invoke it directly.

        Args:
            request: The incoming request — used for partial-render filtering and
                SSR pre-fetch.
        """
        if self._async_prepass_done:
            return
        info = _get_inertia_request_info(request)
        partial_data = info.partial_keys if info.is_partial_render and info.partial_keys else None
        partial_except = info.partial_except_keys if info.is_partial_render and info.partial_except_keys else None
        except_once_props = info.except_once_keys or None

        await resolve_async_props(
            get_raw_shared_props(request),
            partial_data=partial_data,
            partial_except=partial_except,
            except_once_props=except_once_props,
        )

        await resolve_async_props(
            self.content, partial_data=partial_data, partial_except=partial_except, except_once_props=except_once_props
        )

        if self._will_render_ssr(request, info):
            await self._prefetch_ssr(request, info, partial_data, partial_except)

        self._async_prepass_done = True

    async def _prefetch_ssr(
        self,
        request: "Request[Any, Any, Any]",
        info: "_InertiaRequestInfo",
        partial_data: "set[str] | None",
        partial_except: "set[str] | None",
    ) -> None:
        """Build page-props and fetch SSR HTML via BaseIPCTransport."""
        vite_plugin = request.app.plugins.get(VitePlugin)
        inertia_plugin = request.app.plugins.get(InertiaPlugin)
        ssr_config = inertia_plugin.config.ssr_config
        if ssr_config is None:
            return
        page_props = self._build_page_props(
            request,
            partial_data,
            partial_except,
            info.is_partial_render,
            info.except_once_keys,
            info.reset_keys,
            vite_plugin,
            inertia_plugin,
        )
        self._cached_page_props = page_props
        type_encoders = self._resolve_type_encoders(request)

        circuit_breaker = getattr(inertia_plugin, "circuit_breaker", None)
        if circuit_breaker is not None and not circuit_breaker.allow_request():
            logger.debug("Inertia SSR bypassed by circuit breaker; serving client-side hydration.")
            self._cached_ssr_payload = None
            return

        plugin_transport: BaseIPCTransport | str | None = getattr(inertia_plugin, "ipc_transport", None)
        if plugin_transport is None:
            plugin_transport = getattr(inertia_plugin, "_ipc_transport", None)

        transport: BaseIPCTransport | str = (
            plugin_transport if plugin_transport is not None else vite_plugin.get_ipc_transport()
        )

        try:
            self._cached_ssr_payload = await _render_inertia_ssr(
                page_props.to_dict(), transport, ssr_config.timeout, type_encoders=type_encoders
            )
            if circuit_breaker is not None:
                circuit_breaker.record_success()
        except Exception as exc:
            if circuit_breaker is not None:
                circuit_breaker.record_failure(exc)

            if not getattr(ssr_config, "fallback_to_client", True):
                raise

            logger.warning(
                "Inertia SSR request failed (%s: %s); falling back to client-side hydration.", type(exc).__name__, exc
            )
            self._cached_ssr_payload = None

    def _resolve_type_encoders(self, request: "Request[Any, Any, Any]") -> "TypeEncodersMap":
        route_handler = cast("Any | None", request.scope.get("route_handler"))  # pyright: ignore[reportUnknownMemberType]
        route_type_encoders: "TypeEncodersMap" = {}
        if route_handler is not None:
            route_type_encoders = cast("TypeEncodersMap", route_handler.resolve_type_encoders())
        return {**route_type_encoders, **self.response_type_encoders}

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

        if not self._async_prepass_done:
            partial_data_for_check = (
                inertia_info.partial_keys if inertia_info.is_partial_render and inertia_info.partial_keys else None
            )
            partial_except_for_check = (
                inertia_info.partial_except_keys
                if inertia_info.is_partial_render and inertia_info.partial_except_keys
                else None
            )
            needs_props_resolve = has_unresolved_async_props(
                self.content,
                partial_data=partial_data_for_check,
                partial_except=partial_except_for_check,
                except_once_props=inertia_info.except_once_keys or None,
            ) or has_unresolved_async_props(
                get_raw_shared_props(request),
                partial_data=partial_data_for_check,
                partial_except=partial_except_for_check,
                except_once_props=inertia_info.except_once_keys or None,
            )
            needs_ssr = self._will_render_ssr(cast("Request[Any, Any, Any]", request), inertia_info)
            if needs_props_resolve:
                msg = (
                    "InertiaResponse contains unresolved async prop callbacks. "
                    "InertiaPlugin must be registered so route handlers are wrapped "
                    "and async props resolve before request-scoped dependencies are released."
                )
                raise ImproperlyConfiguredException(msg)
            if needs_ssr:
                return cast(
                    "ASGIResponse",
                    _AsyncInertiaSSRResponse(
                        response=self,
                        app=app,
                        request=cast("Request[Any, Any, Any]", request),
                        kwargs={
                            "background": background,
                            "cookies": cookies,
                            "encoded_headers": encoded_headers,
                            "headers": headers,
                            "is_head_response": is_head_response,
                            "media_type": media_type,
                            "status_code": status_code,
                            "type_encoders": type_encoders,
                        },
                    ),
                )
        headers = self.headers if headers is None else ({**headers, **self.headers} if self.headers else headers)
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)
        type_encoders = (
            {**type_encoders, **(self.response_type_encoders or {})} if type_encoders else self.response_type_encoders
        )
        serializer = get_serializer(type_encoders)
        resolved_status_code = (
            status_code
            if self._defer_status_to_handler and status_code is not None
            else (self.status_code or status_code)
        )

        if not inertia_info.inertia_enabled:
            resolved_media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            return ASGIResponse(
                background=self.background or background,
                body=self.render(self.content, resolved_media_type, serializer),
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=resolved_media_type,
                status_code=resolved_status_code,
            )

        vite_plugin = request.app.plugins.get(VitePlugin)
        inertia_plugin = request.app.plugins.get(InertiaPlugin)
        headers.update({
            "Vary": InertiaHeaders.ENABLED.value,
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

        page_props = (
            self._cached_page_props
            if self._cached_page_props is not None
            else self._build_page_props(
                request,
                partial_data,
                partial_except,
                inertia_info.is_partial_render,
                inertia_info.except_once_keys,
                inertia_info.reset_keys,
                vite_plugin,
                inertia_plugin,
            )
        )

        if inertia_info.is_inertia:
            resolved_media_type = get_enum_string_value(self.media_type or media_type or MediaType.JSON)
            body = self.render(page_props.to_dict(), resolved_media_type, serializer)
            return ASGIResponse(  # pyright: ignore[reportUnknownMemberType]
                background=self.background or background,
                body=body,
                cookies=cookies,
                encoded_headers=encoded_headers,
                encoding=self.encoding,
                headers=headers,
                is_head_response=is_head_response,
                media_type=resolved_media_type,
                status_code=resolved_status_code,
            )

        resolved_media_type = self._determine_media_type(self.media_type)

        if vite_plugin.config.wants_spa_config:
            body = self._render_spa(request, page_props, vite_plugin)
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
            status_code=resolved_status_code,
        )


class InertiaExternalRedirect(Response[Any]):
    """External redirect via Inertia protocol or standard HTTP redirect.

    For Inertia XHR requests, responds with a 409 Conflict status and an
    X-Inertia-Location header containing the destination URL. Inertia.js intercepts
    this response and triggers a client-side hard window.location redirect.

    For standard non-Inertia clients (plain browser navigations, cURL, web crawlers,
    OAuth callbacks), responds with a standard HTTP redirect (307 Temporary Redirect
    for GET, 303 See Other for non-GET methods) and a Location header so non-Inertia
    consumers can navigate normally.

    Unlike InertiaRedirect, this does NOT validate the redirect URL as same-origin
    because external redirects are explicitly intended for cross-origin navigation
    (e.g., OAuth callbacks, external payment pages).

    Note:
        Request cookies are intentionally NOT passed to the response to prevent
        cookie leakage in redirect responses.
    """

    def __init__(self, request: "Request[Any, Any, Any]", redirect_to: "str", **kwargs: "Any") -> None:
        """Initialize external redirect.

        Args:
            request: The request object.
            redirect_to: The URL to redirect to (can be external).
            **kwargs: Additional keyword arguments passed to the Response constructor.
        """
        persist_transient_state_for_redirect(request)
        location = quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")
        if bool(InertiaDetails(request)):
            super().__init__(
                content=b"", status_code=HTTP_409_CONFLICT, headers={InertiaHeaders.LOCATION.value: location}, **kwargs
            )
        else:
            super().__init__(
                content=b"",
                status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
                headers={"Location": location},
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
        persist_transient_state_for_redirect(request)
        safe_url = _get_redirect_url(request, redirect_to)
        if _should_use_fragment_redirect(request, safe_url):
            self._uses_inertia_fragment_redirect = True
            Response.__init__(  # pyright: ignore[reportUnknownMemberType]
                self,
                content=b"",
                status_code=HTTP_409_CONFLICT,
                headers={InertiaHeaders.REDIRECT.value: quote(safe_url, safe="/#%[]=:;$&()+,!?*@'~")},
                **kwargs,
            )
        else:
            self._uses_inertia_fragment_redirect = False
            super().__init__(  # pyright: ignore[reportUnknownMemberType]
                path=safe_url,
                status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
                **kwargs,
            )

    def to_asgi_response(
        self,
        app: "Litestar | None",
        request: "Request[Any, Any, Any]",
        *,
        background: "BackgroundTask | BackgroundTasks | None" = None,
        cookies: "Iterable[Cookie] | None" = None,
        encoded_headers: "Iterable[tuple[bytes, bytes]] | None" = None,
        headers: "dict[str, str] | None" = None,
        is_head_response: bool = False,
        media_type: "MediaType | str | None" = None,
        status_code: "int | None" = None,
        type_encoders: "TypeEncodersMap | None" = None,
    ) -> "ASGIResponse":
        if self._uses_inertia_fragment_redirect:
            return Response.to_asgi_response(  # pyright: ignore[reportUnknownMemberType]
                self,
                app=app,
                request=request,
                background=background,
                cookies=cookies,
                encoded_headers=encoded_headers,
                headers=headers,
                is_head_response=is_head_response,
                media_type=media_type,
                status_code=status_code,
                type_encoders=type_encoders,
            )
        return super().to_asgi_response(  # pyright: ignore[reportUnknownMemberType]
            app=app,
            request=request,
            background=background,
            cookies=cookies,
            encoded_headers=encoded_headers,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=status_code,
            type_encoders=type_encoders,
        )


class InertiaBack(InertiaRedirect):
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
        safe_url = _get_redirect_url(request, request.headers.get(InertiaHeaders.REFERER.value))
        super().__init__(request=request, redirect_to=safe_url, **kwargs)


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
    except_once_keys: set[str]
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
            except_once_keys=request.except_once_props_keys,
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
        except_once_keys=set(details.except_once_props_keys),
        reset_keys=set(details.reset_keys),
    )


_SSR_MAX_RESPONSE_BYTES = 10 * 1024 * 1024


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

    total_size = len(body) + sum(len(h) for h in head_list)
    if total_size > _SSR_MAX_RESPONSE_BYTES:
        msg = (
            f"Inertia SSR response from {url!r} exceeds maximum allowed size "
            f"({total_size:,} bytes > {_SSR_MAX_RESPONSE_BYTES:,} bytes). "
            "This may indicate a misconfigured SSR server."
        )
        raise ImproperlyConfiguredException(msg)

    return _InertiaSSRResult(head=cast("list[str]", head_list), body=body)


async def _render_inertia_ssr(
    page: dict[str, Any],
    transport: "BaseIPCTransport | str",
    timeout_seconds: float,
    *,
    type_encoders: "TypeEncodersMap | None" = None,
) -> _InertiaSSRResult:
    """Call the Inertia SSR IPC transport asynchronously and return head/body HTML.

    Args:
        page: The page object to send to the SSR worker.
        transport: The BaseIPCTransport instance or TCP URL string.
        timeout_seconds: Request timeout in seconds.
        type_encoders: Optional type encoders used to serialize page props.

    Returns:
        An _InertiaSSRResult with head and body HTML.
    """
    return await _do_ssr_request(page, transport, timeout_seconds, type_encoders=type_encoders)


async def _do_ssr_request(
    page: dict[str, Any],
    transport: "BaseIPCTransport | str",
    timeout_seconds: float,
    *,
    type_encoders: "TypeEncodersMap | None" = None,
) -> _InertiaSSRResult:
    """Execute the SSR request using BaseIPCTransport.

    Args:
        page: The page object to send to the SSR worker.
        transport: The BaseIPCTransport instance or TCP URL string.
        timeout_seconds: Request timeout in seconds.
        type_encoders: Optional type encoders used to serialize page props.

    Raises:
        ImproperlyConfiguredException: If the SSR worker or transport fails.

    Returns:
        An _InertiaSSRResult with head and body HTML.
    """
    target_label = str(transport)
    if isinstance(transport, str):
        from litestar_vite.ipc import TCPStreamIPCTransport

        parsed = urlparse(transport)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5173
        path = parsed.path or "/__litestar_ssr__"
        transport = TCPStreamIPCTransport(host=host, port=port, path=path)

    serializer = get_serializer(type_encoders)
    encoded_page = decode_json(encode_json(page, serializer=serializer))
    ipc_payload: dict[str, Any] = {"method": "render", "params": encoded_page}

    try:
        raw_payload = await transport.send_request(ipc_payload, timeout=timeout_seconds)
    except Exception as exc:
        msg = f"Inertia SSR execution failed over {transport.__class__.__name__} ({target_label}): {exc}"
        raise ImproperlyConfiguredException(msg) from exc

    if "error" in raw_payload:
        error_info = raw_payload.get("error", "Unknown IPC worker error")
        msg = f"Inertia SSR execution failed over {transport.__class__.__name__} ({target_label}): {error_info}"
        raise ImproperlyConfiguredException(msg)

    result_payload = raw_payload.get("result", raw_payload)
    return _parse_inertia_ssr_payload(result_payload, target_label)


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


def _should_use_fragment_redirect(request: "Request[Any, Any, Any]", url: str) -> bool:
    return bool(InertiaDetails(request)) and bool(urlparse(url).fragment)


def _get_route_prop_key(route_handler: Any) -> str:
    return (route_handler.opt.get("key", "items") if route_handler else "items") or "items"


def _get_explicit_scroll_props_key(route_prop_keys: list[str], route_handler: Any) -> str:
    if len(route_prop_keys) == 1:
        return route_prop_keys[0]
    return _get_route_prop_key(route_handler)


def _apply_pagination_props(
    shared_props: "dict[str, Any]",
    *,
    route_handler: Any,
    explicit_scroll_props: "ScrollPropsConfig | None",
    explicit_scroll_props_key: str,
) -> "dict[str, ScrollPropsConfig] | None":
    scroll_props_map: "dict[str, ScrollPropsConfig]" = {}
    if explicit_scroll_props is not None:
        scroll_props_map[explicit_scroll_props_key] = explicit_scroll_props

    infinite_scroll_enabled = bool(route_handler and route_handler.opt.get("infinite_scroll", False))
    for key in tuple(shared_props):
        value = shared_props[key]
        if is_pagination_container(value):
            _, scroll = extract_pagination_scroll_props(value)
            if scroll is not None and infinite_scroll_enabled and key not in scroll_props_map:
                scroll_props_map[key] = scroll

            pagination_dict = pagination_to_dict(value)
            shared_props[key] = pagination_dict.pop("items")
            shared_props.update(pagination_dict)

    return scroll_props_map or None


def _resolve_deferred_props(
    deferred_props_map: "dict[str, list[str]]", is_partial_render: bool
) -> "dict[str, list[str]] | None":
    return None if is_partial_render else deferred_props_map or None


def _resolve_encrypt_history(encrypt_history: "bool | None", inertia_plugin: "InertiaPlugin") -> bool:
    return inertia_plugin.config.encrypt_history if encrypt_history is None else encrypt_history


def _resolve_clear_history(clear_history: bool, request: "Request[Any, Any, Any]") -> bool:
    local_clear_history = consume_clear_history(request)
    session_clear_history = False
    with contextlib.suppress(AttributeError, ImproperlyConfiguredException):
        session_clear_history = cast(
            "bool",
            request.session.pop("_inertia_clear_history", False),  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
        )
    return clear_history or local_clear_history or session_clear_history


def _merge_deferred_props(target: "dict[str, list[str]]", source: "Mapping[str, list[str]]") -> None:
    for group, keys in source.items():
        group_keys = target.setdefault(group, [])
        for key in keys:
            if key not in group_keys:
                group_keys.append(key)


def _discard_deferred_prop_key(target: "dict[str, list[str]]", key: str) -> None:
    for group in tuple(target):
        group_keys = target[group]
        group_keys[:] = [
            prop_key
            for prop_key in group_keys
            if prop_key != key and not prop_key.startswith(f"{key}.") and prop_key.rsplit(".", maxsplit=1)[-1] != key
        ]
        if not group_keys:
            del target[group]


def _dedupe_once_prop_entries(
    entries: "Iterable[str | tuple[str, str]]", *, reset_keys: "set[str]"
) -> "list[str | tuple[str, str]]":
    filtered: "dict[str, str | tuple[str, str]]" = {}
    for entry in entries:
        key, prop_path = entry if isinstance(entry, tuple) else (entry, entry)
        if key in reset_keys or prop_path in reset_keys:
            continue
        filtered.setdefault(key, entry)
    return list(filtered.values())


class _AsyncInertiaSSRResponse:
    """ASGI response placeholder for SSR HTTP pre-fetch.

    Async prop callbacks are not resolved here because ASGI dispatch happens
    after Litestar's yield-based dependency cleanup. The handler wrapper must
    resolve those callbacks before this object is created.
    """

    __slots__ = ("_app", "_kwargs", "_request", "_response")

    def __init__(
        self,
        *,
        response: "InertiaResponse[Any]",
        app: "Litestar | None",
        request: "Request[Any, Any, Any]",
        kwargs: "dict[str, Any]",
    ) -> None:
        self._response = response
        self._app = app
        self._request = request
        self._kwargs = kwargs

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        info = _get_inertia_request_info(self._request)
        partial_data = info.partial_keys if info.is_partial_render and info.partial_keys else None
        partial_except = info.partial_except_keys if info.is_partial_render and info.partial_except_keys else None
        await self._response._prefetch_ssr(self._request, info, partial_data, partial_except)  # pyright: ignore[reportPrivateUsage]
        self._response._async_prepass_done = True  # pyright: ignore[reportPrivateUsage]
        asgi_response = self._response.to_asgi_response(self._app, self._request, **self._kwargs)
        await asgi_response(scope, receive, send)
