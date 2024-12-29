from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager
from functools import lru_cache
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

from anyio.from_thread import BlockingPortal, start_blocking_portal
from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState
from markupsafe import Markup
from typing_extensions import ParamSpec, TypeGuard

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

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
def lazy(key: str, value_or_callable: Callable[..., None] = ...) -> DeferredProp[str, None]: ...


@overload
def lazy(key: str, value_or_callable: Callable[..., Coroutine[Any, Any, None]] = ...) -> DeferredProp[str, None]: ...


@overload
def lazy(
    key: str,
    value_or_callable: Callable[..., T | Coroutine[Any, Any, T]] = ...,  # pyright: ignore[reportInvalidTypeVarUse]
) -> DeferredProp[str, T]: ...


def lazy(
    key: str,
    value_or_callable: None
    | Callable[T_ParamSpec, None | Coroutine[Any, Any, None]]
    | T
    | Callable[T_ParamSpec, T | Coroutine[Any, Any, T]] = None,
) -> StaticProp[str, None] | StaticProp[str, T] | DeferredProp[str, T] | DeferredProp[str, None]:
    """Wrap an async function to return a DeferredProp."""
    if value_or_callable is None:
        return StaticProp[str, None](key=key, value=None)

    if not callable(value_or_callable):
        return StaticProp[str, T](key=key, value=value_or_callable)

    return DeferredProp[str, T](key=key, value=cast("Callable[..., T | Coroutine[Any, Any, T]]", value_or_callable))


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

    def __init__(
        self, key: PropKeyT, value: Callable[..., None | T | Coroutine[Any, Any, T | None]] | None = None
    ) -> None:
        self._key = key
        self._value = value
        self._evaluated = False
        self._result: T | None = None

    @property
    def key(self) -> PropKeyT:
        return self._key

    @contextmanager
    def with_portal(self, portal: BlockingPortal | None = None) -> Generator[BlockingPortal, None, None]:
        if portal is None:
            with start_blocking_portal() as p:
                yield p
        else:
            yield portal

    @staticmethod
    def _is_awaitable(
        v: Callable[..., T | Coroutine[Any, Any, T]],
    ) -> TypeGuard[Coroutine[Any, Any, T]]:
        return inspect.iscoroutinefunction(v)

    def render(self, portal: BlockingPortal | None = None) -> T | None:
        if self._evaluated:
            return self._result
        if self._value is None or not callable(self._value):
            self._result = self._value
            self._evaluated = True
            return self._result
        if not self._is_awaitable(cast("Callable[..., T]", self._value)):
            self._result = cast("T", self._value())
            self._evaluated = True
            return self._result
        with self.with_portal(portal) as p:
            self._result = p.call(cast("Callable[..., T]", self._value))
            self._evaluated = True
            return self._result


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
                k: lazy_render(v, partial_data, portal)
                for k, v in cast("Mapping[str, Any]", value).items()
                if should_render(v, partial_data)
            },
        )

    if isinstance(value, (list, tuple)):
        filtered = [
            lazy_render(v, partial_data, portal) for v in cast("Iterable[Any]", value) if should_render(v, partial_data)
        ]
        return cast("T", type(value)(filtered))  # pyright: ignore[reportUnknownArgumentType]

    if is_lazy_prop(value) and should_render(value, partial_data):
        return cast("T", value.render(portal))

    return cast("T", value)


def get_shared_props(
    request: ASGIConnection[Any, Any, Any, Any],
    partial_data: set[str] | None = None,
) -> dict[str, Any]:
    """Return shared session props for a request.

    Args:
        request: The ASGI connection.
        partial_data: Optional set of keys for partial rendering.
        portal: Optional portal to use for async rendering
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
        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))

        # Handle deferred props
        for key, value in shared_props.items():
            if is_lazy_prop(value) and should_render(value, partial_data):
                props[key] = value.render(inertia_plugin.portal)
                continue
            if should_render(value, partial_data):
                props[key] = value

        for message in cast("List[Dict[str,Any]]", request.session.pop("_messages", [])):
            flash[message["category"]].append(message["message"])

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
