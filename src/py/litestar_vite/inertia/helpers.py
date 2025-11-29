import inspect
from collections import defaultdict
from collections.abc import Callable, Coroutine, Generator, Iterable, Mapping
from contextlib import contextmanager
from functools import lru_cache
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeGuard, TypeVar, cast, overload

from anyio.from_thread import BlockingPortal, start_blocking_portal
from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState
from markupsafe import Markup
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

    from litestar_vite.inertia.plugin import InertiaPlugin
    from litestar_vite.inertia.routes import Routes

T = TypeVar("T")
T_ParamSpec = ParamSpec("T_ParamSpec")
PropKeyT = TypeVar("PropKeyT", bound=str)
StaticT = TypeVar("StaticT", bound=object)

# Default group for deferred props
DEFAULT_DEFERRED_GROUP = "default"


@overload
def lazy(key: str, value_or_callable: "None") -> "StaticProp[str, None]": ...


@overload
def lazy(key: str, value_or_callable: "T") -> "StaticProp[str, T]": ...


@overload
def lazy(key: str, value_or_callable: "Callable[..., None]" = ...) -> "DeferredProp[str, None]": ...


@overload
def lazy(
    key: str, value_or_callable: "Callable[..., Coroutine[Any, Any, None]]" = ...
) -> "DeferredProp[str, None]": ...


@overload
def lazy(
    key: str,
    value_or_callable: "Callable[..., T | Coroutine[Any, Any, T]]" = ...,  # pyright: ignore[reportInvalidTypeVarUse]
) -> "DeferredProp[str, T]": ...


def lazy(
    key: str,
    value_or_callable: "T | Callable[..., Coroutine[Any, Any, None]] | Callable[..., T] | Callable[..., T | Coroutine[Any, Any, T]] | None" = None,
) -> "StaticProp[str, None] | StaticProp[str, T] | DeferredProp[str, T] | DeferredProp[str, None]":
    """Wrap an async function to return a DeferredProp.

    Args:
        key: The key to store the value under.
        value_or_callable: The value or callable to store.

    Returns:
        The wrapped value or callable.
    """
    if value_or_callable is None:
        return StaticProp[str, None](key=key, value=None)

    if not callable(value_or_callable):
        return StaticProp[str, T](key=key, value=value_or_callable)

    return DeferredProp[str, T](
        key=key,
        value=cast("Callable[..., T | Coroutine[Any, Any, T]]", value_or_callable),
    )


def defer(
    key: str,
    callback: "Callable[..., T | Coroutine[Any, Any, T]]",
    group: str = DEFAULT_DEFERRED_GROUP,
) -> "DeferredProp[str, T]":
    """Create a deferred prop with optional grouping (v2 feature).

    Deferred props are loaded lazily after the initial page render.
    Props in the same group are fetched together in a single request.

    Args:
        key: The key to store the value under.
        callback: A callable (sync or async) that returns the value.
        group: The group name for batched loading. Defaults to "default".

    Returns:
        A DeferredProp instance.

    Example::

        # Basic deferred prop
        defer("permissions", lambda: Permission.all())

        # Grouped deferred props (fetched together)
        defer("teams", lambda: Team.all(), group="attributes")
        defer("projects", lambda: Project.all(), group="attributes")
    """
    return DeferredProp[str, T](
        key=key,
        value=callback,
        group=group,
    )


class MergeProp(Generic[PropKeyT, T]):
    """A wrapper for merge prop configuration (v2 feature).

    Merge props allow data to be combined with existing props during
    partial reloads instead of replacing them entirely.
    """

    def __init__(
        self,
        key: "PropKeyT",
        value: "T",
        strategy: "Literal['append', 'prepend', 'deep']" = "append",
        match_on: "str | list[str] | None" = None,
    ) -> None:
        """Initialize a MergeProp.

        Args:
            key: The prop key.
            value: The value to merge.
            strategy: The merge strategy - 'append', 'prepend', or 'deep'.
            match_on: Optional key(s) to match items on during merge.
        """
        self._key = key
        self._value = value
        self._strategy = strategy
        self._match_on = [match_on] if isinstance(match_on, str) else match_on

    @property
    def key(self) -> "PropKeyT":
        """The prop key."""
        return self._key

    @property
    def value(self) -> "T":
        """The value to merge."""
        return self._value

    @property
    def strategy(self) -> "Literal['append', 'prepend', 'deep']":
        """The merge strategy."""
        return self._strategy  # pyright: ignore[reportReturnType]

    @property
    def match_on(self) -> "list[str] | None":
        """Keys to match items on during merge."""
        return self._match_on


def merge(
    key: str,
    value: "T",
    strategy: "Literal['append', 'prepend', 'deep']" = "append",
    match_on: "str | list[str] | None" = None,
) -> "MergeProp[str, T]":
    """Create a merge prop for combining data during partial reloads (v2 feature).

    Merge props allow new data to be combined with existing props rather than
    replacing them entirely. This is useful for infinite scroll, load more buttons,
    and similar patterns.

    Note: Prop merging only works during partial reloads. Full page visits
    will always replace props entirely.

    Args:
        key: The prop key.
        value: The value to merge.
        strategy: How to merge the data:
            - 'append': Add new items to the end (default)
            - 'prepend': Add new items to the beginning
            - 'deep': Recursively merge nested objects
        match_on: Optional key(s) to match items on during merge,
            useful for updating existing items instead of duplicating.

    Returns:
        A MergeProp instance.

    Example::

        # Append new items to existing list
        merge("posts", new_posts)

        # Prepend new messages
        merge("messages", new_messages, strategy="prepend")

        # Deep merge nested data
        merge("user_data", updates, strategy="deep")

        # Match on ID to update existing items
        merge("posts", updated_posts, match_on="id")
    """
    return MergeProp[str, T](key=key, value=value, strategy=strategy, match_on=match_on)


def is_merge_prop(value: "Any") -> "TypeGuard[MergeProp[Any, Any]]":
    """Check if value is a MergeProp.

    Args:
        value: Any value to check

    Returns:
        bool: True if value is a MergeProp
    """
    return isinstance(value, MergeProp)


def extract_merge_props(props: "dict[str, Any]") -> "tuple[list[str], list[str], list[str], dict[str, list[str]]]":
    """Extract merge props metadata for the Inertia v2 protocol.

    This extracts all MergeProp instances from the props dict and categorizes them
    by their merge strategy, returning the appropriate lists for the page response.

    Args:
        props: The props dictionary to scan.

    Returns:
        A tuple of (merge_props, prepend_props, deep_merge_props, match_props_on)
        where each list contains the prop keys for that strategy, and match_props_on
        is a dict mapping prop keys to the keys to match on.

    Example::

        props = {
            "users": [...],  # regular prop
            "posts": merge("posts", new_posts),  # append
            "messages": merge("messages", new_msgs, strategy="prepend"),
            "data": merge("data", updates, strategy="deep"),
            "items": merge("items", items, match_on="id"),
        }
        merge_props, prepend_props, deep_merge_props, match_props_on = extract_merge_props(props)
        # merge_props = ["posts", "items"]
        # prepend_props = ["messages"]
        # deep_merge_props = ["data"]
        # match_props_on = {"items": ["id"]}
    """
    merge_list: "list[str]" = []
    prepend_list: "list[str]" = []
    deep_merge_list: "list[str]" = []
    match_on_dict: "dict[str, list[str]]" = {}

    for key, value in props.items():
        if is_merge_prop(value):
            if value.strategy == "append":
                merge_list.append(key)
            elif value.strategy == "prepend":
                prepend_list.append(key)
            elif value.strategy == "deep":
                deep_merge_list.append(key)

            if value.match_on:
                match_on_dict[key] = value.match_on

    return merge_list, prepend_list, deep_merge_list, match_on_dict


class StaticProp(Generic[PropKeyT, StaticT]):
    """A wrapper for static property evaluation."""

    def __init__(self, key: "PropKeyT", value: "StaticT") -> None:
        self._key = key
        self._result = value

    @property
    def key(self) -> "PropKeyT":
        return self._key

    def render(self, portal: "BlockingPortal | None" = None) -> "StaticT":
        return self._result


class DeferredProp(Generic[PropKeyT, T]):
    """A wrapper for deferred property evaluation."""

    def __init__(
        self,
        key: "PropKeyT",
        value: "Callable[..., T | Coroutine[Any, Any, T] | None] | None" = None,
        group: str = DEFAULT_DEFERRED_GROUP,
    ) -> None:
        self._key = key
        self._value = value
        self._group = group
        self._evaluated = False
        self._result: "T | None" = None

    @property
    def group(self) -> str:
        """The deferred group this prop belongs to."""
        return self._group

    @property
    def key(self) -> "PropKeyT":
        return self._key

    @staticmethod
    @contextmanager
    def with_portal(portal: "BlockingPortal | None" = None) -> "Generator[BlockingPortal, None, None]":
        if portal is None:
            with start_blocking_portal() as p:
                yield p
        else:
            yield portal

    @staticmethod
    def _is_awaitable(
        v: "Callable[..., T | Coroutine[Any, Any, T]]",
    ) -> "TypeGuard[Coroutine[Any, Any, T]]":
        return inspect.iscoroutinefunction(v)

    def render(self, portal: "BlockingPortal | None" = None) -> "T | None":
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


def is_lazy_prop(value: "Any") -> "TypeGuard[DeferredProp[Any, Any] | StaticProp[Any, Any]]":
    """Check if value is a deferred property.

    Args:
        value: Any value to check

    Returns:
        bool: True if value is a deferred property
    """
    return isinstance(value, (DeferredProp, StaticProp))


def is_deferred_prop(value: "Any") -> "TypeGuard[DeferredProp[Any, Any]]":
    """Check if value is specifically a DeferredProp (not StaticProp).

    Args:
        value: Any value to check

    Returns:
        bool: True if value is a DeferredProp
    """
    return isinstance(value, DeferredProp)


def extract_deferred_props(props: "dict[str, Any]") -> "dict[str, list[str]]":
    """Extract deferred props metadata for the Inertia v2 protocol.

    This extracts all DeferredProp instances from the props dict and groups them
    by their group name, returning a dict mapping group -> list of prop keys.

    Args:
        props: The props dictionary to scan.

    Returns:
        A dict mapping group names to lists of prop keys in that group.
        Empty dict if no deferred props found.

    Example::

        props = {
            "users": [...],  # regular prop
            "teams": defer("teams", get_teams, group="attributes"),
            "projects": defer("projects", get_projects, group="attributes"),
            "permissions": defer("permissions", get_permissions),  # default group
        }
        result = extract_deferred_props(props)
        # {"default": ["permissions"], "attributes": ["teams", "projects"]}
    """
    groups: "dict[str, list[str]]" = {}

    for key, value in props.items():
        if is_deferred_prop(value):
            group = value.group
            if group not in groups:
                groups[group] = []
            groups[group].append(key)

    return groups


def should_render(
    value: "Any",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
) -> "bool":
    """Check if value should be rendered.

    For v2 protocol, partial_except takes precedence over partial_data.

    Args:
        value: Any value to check
        partial_data: Optional set of keys to include (X-Inertia-Partial-Data)
        partial_except: Optional set of keys to exclude (X-Inertia-Partial-Except, v2)

    Returns:
        bool: True if value should be rendered
    """
    if is_lazy_prop(value):
        # v2: partial_except takes precedence - exclude these props
        if partial_except:
            return value.key not in partial_except
        # Original behavior: only include if in partial_data
        if partial_data:
            return value.key in partial_data
        # No filtering specified, don't render lazy props on initial load
        return False
    return True


def is_or_contains_lazy_prop(value: "Any") -> "bool":
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


def lazy_render(
    value: "T",
    partial_data: "set[str] | None" = None,
    portal: "BlockingPortal | None" = None,
    partial_except: "set[str] | None" = None,
) -> "T":
    """Filter deferred properties from the value based on partial data.

    For v2 protocol, partial_except takes precedence over partial_data.

    Args:
        value: The value to filter
        partial_data: Keys to include (X-Inertia-Partial-Data)
        portal: Optional portal to use for async rendering
        partial_except: Keys to exclude (X-Inertia-Partial-Except, v2)

    Returns:
        The filtered value
    """
    if isinstance(value, str):
        return cast("T", value)
    if isinstance(value, Mapping):
        return cast(
            "T",
            {
                k: lazy_render(v, partial_data, portal, partial_except)
                for k, v in cast("Mapping[str, Any]", value).items()
                if should_render(v, partial_data, partial_except)
            },
        )

    if isinstance(value, (list, tuple)):
        filtered = [
            lazy_render(v, partial_data, portal, partial_except)
            for v in cast("Iterable[Any]", value)
            if should_render(v, partial_data, partial_except)
        ]
        return cast("T", type(value)(filtered))  # pyright: ignore[reportUnknownArgumentType]

    if is_lazy_prop(value) and should_render(value, partial_data, partial_except):
        return cast("T", value.render(portal))

    return cast("T", value)


def get_shared_props(
    request: "ASGIConnection[Any, Any, Any, Any]",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
) -> "dict[str, Any]":
    """Return shared session props for a request.

    For v2 protocol, partial_except takes precedence over partial_data.

    Args:
        request: The ASGI connection.
        partial_data: Optional set of keys to include (X-Inertia-Partial-Data).
        partial_except: Optional set of keys to exclude (X-Inertia-Partial-Except, v2).

    Returns:
        Dict[str, Any]: The shared props.

    Note:
        Be sure to call this before `self.create_template_context` if you would like to include the `flash` message details.
    """
    props: "dict[str, Any]" = {}
    flash: "dict[str, list[str]]" = defaultdict(list)
    errors: "dict[str, Any]" = {}
    error_bag = request.headers.get("X-Inertia-Error-Bag", None)

    try:
        errors = request.session.pop("_errors", {})
        shared_props = cast("dict[str,Any]", request.session.pop("_shared", {}))
        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))

        # Handle deferred props
        for key, value in shared_props.items():
            if is_lazy_prop(value) and should_render(value, partial_data, partial_except):
                props[key] = value.render(inertia_plugin.portal)
                continue
            if should_render(value, partial_data, partial_except):
                props[key] = value

        for message in cast("list[dict[str,Any]]", request.session.pop("_messages", [])):
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
    connection: "ASGIConnection[Any, Any, Any, Any]",
    key: "str",
    value: "Any",
) -> "None":
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
    connection: "ASGIConnection[Any, Any, Any, Any]",
    key: "str",
    message: "str",
) -> "None":
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


def js_routes_script(js_routes: "Routes") -> "Markup":
    @lru_cache
    def _markup_safe_json_dumps(js_routes: "str") -> "Markup":
        js = js_routes.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("'", "\\u0027")
        return Markup(js)

    return Markup(
        dedent(f"""
        <script type="module">
        globalThis.routes = JSON.parse('{_markup_safe_json_dumps(js_routes.formatted_routes)}')
        </script>
        """),
    )
