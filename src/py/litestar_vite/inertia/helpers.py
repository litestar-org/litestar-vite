from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeGuard, TypeVar, cast, overload

from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState

from litestar_vite.inertia._async_mixin import AsyncRenderMixin
from litestar_vite.inertia.types import ScrollPropsConfig

if TYPE_CHECKING:
    from anyio.from_thread import BlockingPortal
    from litestar.connection import ASGIConnection

    from litestar_vite.inertia.plugin import InertiaPlugin
T = TypeVar("T")
PropKeyT = TypeVar("PropKeyT", bound=str)
StaticT = TypeVar("StaticT", bound=object)

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
    """Create a lazy prop only included during partial reloads.

    Lazy props are excluded from the initial page load and only sent when
    explicitly requested via partial reload (X-Inertia-Partial-Data header).
    This optimizes initial page load by deferring non-critical data.

    There are two use cases for lazy():

    **1. Static Value (bandwidth optimization)**:
        The value is computed eagerly but only sent during partial reloads.
        Use when the value is cheap to compute but you want to reduce initial payload.

        >>> lazy("user_count", len(users))

    **2. Callable (bandwidth + CPU optimization)**:
        The callable is only invoked during partial reloads.
        Use when the value is expensive to compute.

        >>> lazy("permissions", lambda: Permission.all())

    .. warning:: **False Lazy Pitfall**

        Be careful not to accidentally call the function when passing it.

        Wrong::

            lazy("data", expensive_fn())

        Correct::

            lazy("data", expensive_fn)

        This is a Python evaluation order issue, not a framework limitation.

    Args:
        key: The key to store the value under in the props dict.
        value_or_callable: Either a static value (computed eagerly, sent lazily)
            or a callable (computed and sent lazily). If None, creates a lazy
            prop with None value.

    Returns:
        StaticProp if value_or_callable is not callable, DeferredProp otherwise.

    Example::

        from litestar_vite.inertia import lazy, InertiaResponse

        @get("/dashboard", component="Dashboard")
        async def dashboard() -> InertiaResponse:
            props = {
                "user": current_user,
                "user_count": lazy("user_count", 42),
                "permissions": lazy("permissions", lambda: Permission.all()),
                "notifications": lazy("notifications", fetch_notifications),
            }
            return InertiaResponse(props)

    See Also:
        - :func:`defer`: For v2 grouped deferred props loaded after page render
        - Inertia.js partial reloads: https://inertiajs.com/partial-reloads
    """
    if value_or_callable is None:
        return StaticProp[str, None](key=key, value=None)

    if not callable(value_or_callable):
        return StaticProp[str, T](key=key, value=value_or_callable)

    return DeferredProp[str, T](key=key, value=cast("Callable[..., T | Coroutine[Any, Any, T]]", value_or_callable))


def defer(
    key: str, callback: "Callable[..., T | Coroutine[Any, Any, T]]", group: str = DEFAULT_DEFERRED_GROUP
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

        defer("permissions", lambda: Permission.all())

        defer("teams", lambda: Team.all(), group="attributes")
        defer("projects", lambda: Project.all(), group="attributes")

        # Chain with .once() for lazy + cached behavior
        defer("stats", lambda: compute_expensive_stats()).once()
    """
    return DeferredProp[str, T](key=key, value=callback, group=group)


def once(key: str, value_or_callable: "T | Callable[..., T | Coroutine[Any, Any, T]]") -> "OnceProp[str, T]":
    """Create a prop that resolves once and is cached client-side (v2.2.20+ feature).

    Once props are included in the initial page load and resolved immediately.
    After resolution, the client caches the value and won't request it again
    on subsequent page visits, unless explicitly requested via partial reload.

    This is useful for:
    - Expensive computations that rarely change
    - User preferences or settings
    - Feature flags
    - Static configuration

    Unlike lazy props, once props ARE included in initial loads.
    The "once" behavior tells the client to cache the result.

    Args:
        key: The key to store the value under.
        value_or_callable: Either a static value or a callable that returns the value.

    Returns:
        An OnceProp instance.

    Example::

        from litestar_vite.inertia import once, InertiaResponse

        @get("/dashboard", component="Dashboard")
        async def dashboard() -> InertiaResponse:
            return InertiaResponse({
                "user": current_user,
                "settings": once("settings", lambda: Settings.for_user(user_id)),
                "feature_flags": once("feature_flags", get_feature_flags()),
            })

    See Also:
        - :func:`defer`: For deferred props that support ``.once()`` chaining
        - Inertia.js once props: https://inertiajs.com/partial-reloads#once
    """
    return OnceProp[str, T](key=key, value=value_or_callable)


def optional(key: str, callback: "Callable[..., T | Coroutine[Any, Any, T]]") -> "OptionalProp[str, T]":
    """Create a prop only included when explicitly requested (v2 feature).

    Optional props are NEVER included in initial page loads or standard
    partial reloads. They're only sent when the client explicitly requests
    them via ``only: ['prop_name']`` in a partial reload.

    This is designed for use with Inertia's WhenVisible component, which
    triggers a partial reload requesting specific props when an element
    becomes visible in the viewport.

    The callback is only evaluated when requested, providing both
    bandwidth and CPU optimization.

    Args:
        key: The key to store the value under.
        callback: A callable (sync or async) that returns the value.

    Returns:
        An OptionalProp instance.

    Example::

        from litestar_vite.inertia import optional, InertiaResponse

        @get("/posts/{post_id}", component="Posts/Show")
        async def show_post(post_id: int) -> InertiaResponse:
            post = await Post.get(post_id)
            return InertiaResponse({
                "post": post,
                # Only loaded when WhenVisible triggers
                "comments": optional("comments", lambda: Comment.for_post(post_id)),
                "related_posts": optional("related_posts", lambda: Post.related(post_id)),
            })

    Frontend usage with WhenVisible::

        <WhenVisible data="comments" :params="{ only: ['comments'] }">
            <template #fallback>
                <LoadingSpinner />
            </template>
            <CommentList :comments="comments" />
        </WhenVisible>

    See Also:
        - Inertia.js WhenVisible: https://inertiajs.com/load-when-visible
    """
    return OptionalProp[str, T](key=key, callback=callback)


def always(key: str, value: "T") -> "AlwaysProp[str, T]":
    """Create a prop always included, even during partial reloads (v2 feature).

    Always props bypass partial reload filtering entirely. They're included
    in every response regardless of what keys the client requests.

    Use for critical data that must always be present:
    - Authentication state
    - Permission flags
    - Feature toggles
    - Error states

    Args:
        key: The key to store the value under.
        value: The value (evaluated eagerly).

    Returns:
        An AlwaysProp instance.

    Example::

        from litestar_vite.inertia import always, lazy, InertiaResponse

        @get("/dashboard", component="Dashboard")
        async def dashboard(request: Request) -> InertiaResponse:
            return InertiaResponse({
                # Always sent, even during partial reloads for other props
                "auth": always("auth", {"user": request.user, "can": permissions}),
                # Only sent when explicitly requested
                "analytics": lazy("analytics", get_analytics),
                "reports": lazy("reports", get_reports),
            })

    See Also:
        - :func:`lazy`: For props excluded from initial load
        - :func:`optional`: For props only included when explicitly requested
    """
    return AlwaysProp[str, T](key=key, value=value)


@dataclass
class PropFilter:
    """Configuration for prop filtering during partial reloads.

    Used with ``only()`` and ``except_()`` helpers to explicitly control
    which props are sent during partial reload requests.

    Attributes:
        include: Set of prop keys to include (only send these).
        exclude: Set of prop keys to exclude (send all except these).
    """

    include: "set[str] | None" = None
    exclude: "set[str] | None" = None

    def should_include(self, key: str) -> bool:
        """Return True when a prop key should be included.

        Returns:
            True if the prop key should be included, otherwise False.
        """
        if self.exclude is not None:
            return key not in self.exclude
        if self.include is not None:
            return key in self.include
        return True


def only(*keys: str) -> PropFilter:
    """Create a filter that only includes the specified prop keys.

    Use this to explicitly limit which props are sent during partial reloads.
    Only the specified props will be included in the response.

    Args:
        *keys: The prop keys to include.

    Returns:
        A PropFilter configured to include only the specified keys.

    Example::

        from litestar_vite.inertia import only, InertiaResponse

        @get("/users", component="Users")
        async def list_users(
            request: InertiaRequest,
            user_service: UserService,
        ) -> InertiaResponse:
            return InertiaResponse(
                {
                    "users": user_service.list(),
                    "teams": team_service.list(),
                    "stats": stats_service.get(),
                },
                prop_filter=only("users"),
            )

    Note:
        This is a server-side helper. The client should use Inertia's
        ``router.reload({ only: ['users'] })`` for client-initiated filtering.
    """
    return PropFilter(include=set(keys))


def except_(*keys: str) -> PropFilter:
    """Create a filter that excludes the specified prop keys.

    Use this to explicitly exclude certain props during partial reloads.
    All props except the specified ones will be included in the response.

    Args:
        *keys: The prop keys to exclude.

    Returns:
        A PropFilter configured to exclude the specified keys.

    Example::

        from litestar_vite.inertia import except_, InertiaResponse

        @get("/users", component="Users")
        async def list_users(
            request: InertiaRequest,
            user_service: UserService,
        ) -> InertiaResponse:
            return InertiaResponse(
                {
                    "users": user_service.list(),
                    "teams": team_service.list(),
                    "stats": expensive_stats(),
                },
                prop_filter=except_("stats"),
            )

    Note:
        The function is named ``except_`` with a trailing underscore to avoid
        conflicting with Python's ``except`` keyword.
    """
    return PropFilter(exclude=set(keys))


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
        return self._key

    @property
    def value(self) -> "T":
        return self._value

    @property
    def strategy(self) -> "Literal['append', 'prepend', 'deep']":
        return self._strategy  # pyright: ignore[reportReturnType]

    @property
    def match_on(self) -> "list[str] | None":
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

        merge("posts", new_posts)

        merge("messages", new_messages, strategy="prepend")

        merge("user_data", updates, strategy="deep")

        merge("posts", updated_posts, match_on="id")
    """
    return MergeProp[str, T](key=key, value=value, strategy=strategy, match_on=match_on)


def scroll_props(
    page_name: str = "page", current_page: int = 1, previous_page: "int | None" = None, next_page: "int | None" = None
) -> "ScrollPropsConfig":
    """Create scroll props configuration for infinite scroll (v2 feature).

    Scroll props allow Inertia to manage pagination state for infinite scroll
    patterns, providing next/previous page information to the client.

    Args:
        page_name: The query parameter name for pagination. Defaults to "page".
        current_page: The current page number. Defaults to 1.
        previous_page: The previous page number, or None if at first page.
        next_page: The next page number, or None if at last page.

    Returns:
        A ScrollPropsConfig instance for use in InertiaResponse.

    Example::

        from litestar_vite.inertia import scroll_props, InertiaResponse

        @get("/posts", component="Posts")
        async def list_posts(page: int = 1) -> InertiaResponse:
            posts = await Post.paginate(page=page, per_page=20)
            return InertiaResponse(
                {"posts": merge("posts", posts.items)},
                scroll_props=scroll_props(
                    current_page=page,
                    previous_page=page - 1 if page > 1 else None,
                    next_page=page + 1 if posts.has_more else None,
                ),
            )
    """
    return ScrollPropsConfig(
        page_name=page_name, current_page=current_page, previous_page=previous_page, next_page=next_page
    )


def is_merge_prop(value: "Any") -> "TypeGuard[MergeProp[Any, Any]]":
    """Check if value is a MergeProp.

    Args:
        value: Any value to check

    Returns:
        True if value is a MergeProp
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
            "users": [...],
            "posts": merge("posts", new_posts),
            "messages": merge("messages", new_msgs, strategy="prepend"),
            "data": merge("data", updates, strategy="deep"),
            "items": merge("items", items, match_on="id"),
        }
        merge_props, prepend_props, deep_merge_props, match_props_on = extract_merge_props(props)

        The returned values then contain:

        - merge_props: ["posts", "items"]
        - prepend_props: ["messages"]
        - deep_merge_props: ["data"]
        - match_props_on: {"items": ["id"]}
    """
    merge_list: "list[str]" = []
    prepend_list: "list[str]" = []
    deep_merge_list: "list[str]" = []
    match_on_dict: "dict[str, list[str]]" = {}

    for key, value in props.items():
        if is_merge_prop(value):
            match value.strategy:
                case "append":
                    merge_list.append(key)
                case "prepend":
                    prepend_list.append(key)
                case "deep":
                    deep_merge_list.append(key)
                case _:
                    pass

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

    def render(self, portal: "BlockingPortal | None" = None) -> "StaticT":  # pyright: ignore
        return self._result


class DeferredProp(AsyncRenderMixin, Generic[PropKeyT, T]):
    """A wrapper for deferred property evaluation."""

    def __init__(
        self,
        key: "PropKeyT",
        value: "Callable[..., T | Coroutine[Any, Any, T] | None] | None" = None,
        group: str = DEFAULT_DEFERRED_GROUP,
        is_once: bool = False,
    ) -> None:
        self._key = key
        self._value = value
        self._group = group
        self._is_once = is_once
        self._evaluated = False
        self._result: "T | None" = None

    @property
    def group(self) -> str:
        """The deferred group this prop belongs to.

        Returns:
            The deferred group name.
        """
        return self._group

    @property
    def key(self) -> "PropKeyT":
        return self._key

    @property
    def is_once(self) -> bool:
        """Whether this prop should only be resolved once and cached client-side.

        Returns:
            True if this is a once prop.
        """
        return self._is_once

    def once(self) -> "DeferredProp[PropKeyT, T]":
        """Return a new DeferredProp with once behavior enabled.

        Once props are cached client-side after first resolution.
        They won't be re-fetched on subsequent visits unless explicitly
        requested via partial reload.

        Returns:
            A new DeferredProp with is_once=True.

        Example::

            # Combine defer with once for lazy + cached behavior
            defer("stats", lambda: compute_expensive_stats()).once()
        """
        return DeferredProp[PropKeyT, T](key=self._key, value=self._value, group=self._group, is_once=True)

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


class OnceProp(AsyncRenderMixin, Generic[PropKeyT, T]):
    """A wrapper for once-only property evaluation (v2.2.20+ feature).

    Once props are resolved once and cached client-side. They won't be
    re-fetched on subsequent page visits unless explicitly requested
    via partial reload with ``only: ['key']``.

    This is useful for expensive computations that rarely change
    (e.g., user preferences, feature flags, static configuration).

    Unlike lazy props, once props ARE included in the initial page load.
    The "once" behavior tells the client to cache the value and not
    request it again on future visits.
    """

    def __init__(self, key: "PropKeyT", value: "T | Callable[..., T | Coroutine[Any, Any, T]]") -> None:
        """Initialize a OnceProp.

        Args:
            key: The prop key.
            value: Either a static value or a callable that returns the value.
        """
        self._key = key
        self._value = value
        self._evaluated = False
        self._result: "T | None" = None

    @property
    def key(self) -> "PropKeyT":
        return self._key

    def render(self, portal: "BlockingPortal | None" = None) -> "T | None":
        """Render the prop value, caching the result.

        Args:
            portal: Optional blocking portal for async callbacks.

        Returns:
            The rendered value.
        """
        if self._evaluated:
            return self._result
        if not callable(self._value):
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


class OptionalProp(AsyncRenderMixin, Generic[PropKeyT, T]):
    """A wrapper for optional property evaluation (v2 feature).

    Optional props are NEVER included in initial page loads or standard
    partial reloads. They're only sent when the client explicitly requests
    them via ``only: ['prop_name']``.

    This is designed for use with Inertia's WhenVisible component, which
    loads data only when an element becomes visible in the viewport.

    The callback is only evaluated when the prop is explicitly requested,
    providing both bandwidth and CPU optimization.
    """

    def __init__(self, key: "PropKeyT", callback: "Callable[..., T | Coroutine[Any, Any, T]]") -> None:
        """Initialize an OptionalProp.

        Args:
            key: The prop key.
            callback: A callable that returns the value when requested.
        """
        self._key = key
        self._callback = callback
        self._evaluated = False
        self._result: "T | None" = None

    @property
    def key(self) -> "PropKeyT":
        return self._key

    def render(self, portal: "BlockingPortal | None" = None) -> "T | None":
        """Render the prop value, caching the result.

        Args:
            portal: Optional blocking portal for async callbacks.

        Returns:
            The rendered value.
        """
        if self._evaluated:
            return self._result
        if not self._is_awaitable(cast("Callable[..., T]", self._callback)):
            self._result = cast("T", self._callback())
            self._evaluated = True
            return self._result
        with self.with_portal(portal) as p:
            self._result = p.call(cast("Callable[..., T]", self._callback))
            self._evaluated = True
            return self._result


class AlwaysProp(Generic[PropKeyT, T]):
    """A wrapper for always-included property evaluation (v2 feature).

    Always props are ALWAYS included in responses, even during partial
    reloads. This is the opposite of lazy props - they bypass any
    partial reload filtering.

    Use for critical data that must always be present, such as:
    - Authentication state
    - Permission flags
    - Feature toggles
    - Error states
    """

    def __init__(self, key: "PropKeyT", value: "T") -> None:
        """Initialize an AlwaysProp.

        Args:
            key: The prop key.
            value: The value (always evaluated eagerly).
        """
        self._key = key
        self._value = value

    @property
    def key(self) -> "PropKeyT":
        return self._key

    @property
    def value(self) -> "T":
        return self._value

    def render(self, portal: "BlockingPortal | None" = None) -> "T":  # pyright: ignore
        """Return the prop value.

        Args:
            portal: Unused, included for interface consistency.

        Returns:
            The prop value.
        """
        return self._value


def is_lazy_prop(value: "Any") -> "TypeGuard[DeferredProp[Any, Any] | StaticProp[Any, Any]]":
    """Check if value is a lazy property (StaticProp or DeferredProp).

    Lazy props are excluded from initial page loads and only sent when
    explicitly requested via partial reload.

    Args:
        value: Any value to check

    Returns:
        True if value is a lazy property (StaticProp or DeferredProp)
    """
    return isinstance(value, (DeferredProp, StaticProp))


def is_once_prop(value: "Any") -> "TypeGuard[OnceProp[Any, Any]]":
    """Check if value is a once prop.

    Once props are included in initial loads but cached client-side.

    Args:
        value: Any value to check

    Returns:
        True if value is an OnceProp
    """
    return isinstance(value, OnceProp)


def is_optional_prop(value: "Any") -> "TypeGuard[OptionalProp[Any, Any]]":
    """Check if value is an optional prop.

    Optional props are only included when explicitly requested.

    Args:
        value: Any value to check

    Returns:
        True if value is an OptionalProp
    """
    return isinstance(value, OptionalProp)


def is_always_prop(value: "Any") -> "TypeGuard[AlwaysProp[Any, Any]]":
    """Check if value is an always prop.

    Always props bypass partial reload filtering.

    Args:
        value: Any value to check

    Returns:
        True if value is an AlwaysProp
    """
    return isinstance(value, AlwaysProp)


def is_special_prop(value: "Any") -> bool:
    """Check if value is any special prop type (lazy, once, optional, always).

    Args:
        value: Any value to check

    Returns:
        True if value is a special prop wrapper
    """
    return isinstance(value, (DeferredProp, StaticProp, OnceProp, OptionalProp, AlwaysProp))


def is_deferred_prop(value: "Any") -> "TypeGuard[DeferredProp[Any, Any]]":
    """Check if value is specifically a DeferredProp (not StaticProp).

    Args:
        value: Any value to check

    Returns:
        True if value is a DeferredProp
    """
    return isinstance(value, DeferredProp)


def extract_deferred_props(props: "dict[str, Any]") -> "dict[str, list[str]]":
    """Extract deferred props metadata for the Inertia v2 protocol.

    This extracts all DeferredProp instances from the props dict and groups them
    by their group name, returning a dict mapping group -> list of prop keys.

    Note: DeferredProp instances with is_once=True are excluded from the result
    because once props should not be re-fetched after initial resolution.

    Args:
        props: The props dictionary to scan.

    Returns:
        A dict mapping group names to lists of prop keys in that group.
        Empty dict if no deferred props found.

    Example::

        props = {
            "users": [...],
            "teams": defer("teams", get_teams, group="attributes"),
            "projects": defer("projects", get_projects, group="attributes"),
            "permissions": defer("permissions", get_permissions),
        }
        result = extract_deferred_props(props)

        The result is {"default": ["permissions"], "attributes": ["teams", "projects"]}.
    """
    groups: "dict[str, list[str]]" = {}

    for key, value in props.items():
        if is_deferred_prop(value):
            # Exclude once props from deferred metadata
            if value.is_once:
                continue
            group = value.group
            if group not in groups:
                groups[group] = []
            groups[group].append(key)

    return groups


def extract_once_props(props: "dict[str, Any]") -> "list[str]":
    """Extract once props for the Inertia v2.2.20+ protocol.

    Once props are cached client-side after first resolution. This function
    extracts all OnceProp instances and DeferredProp instances with is_once=True.

    Args:
        props: The props dictionary to scan.

    Returns:
        A list of prop keys that should be cached client-side.
        Empty list if no once props found.

    Example::

        props = {
            "user": current_user,
            "settings": once("settings", get_settings),
            "stats": defer("stats", get_stats).once(),
        }
        result = extract_once_props(props)

        The result is ["settings", "stats"].
    """
    once_keys: "list[str]" = []

    for key, value in props.items():
        if is_once_prop(value) or (is_deferred_prop(value) and value.is_once):
            once_keys.append(key)

    return once_keys


def should_render(  # noqa: PLR0911
    value: "Any",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    key: "str | None" = None,
) -> "bool":
    """Check if value should be rendered based on partial reload filtering.

    For v2 protocol, partial_except takes precedence over partial_data.
    When a key is provided, filtering applies to all props (not just lazy props).

    Prop types have different behaviors:
    - **AlwaysProp**: Always included, bypasses all filtering
    - **OptionalProp**: Only included when explicitly requested via partial_data
    - **LazyProp** (StaticProp/DeferredProp): Excluded from initial load, included on partial reload
    - **OnceProp**: Included in initial load, cached client-side
    - **Regular values**: Follow standard partial reload filtering

    Args:
        value: Any value to check
        partial_data: Optional set of keys to include (X-Inertia-Partial-Data)
        partial_except: Optional set of keys to exclude (X-Inertia-Partial-Except, v2)
        key: Optional key name for this prop (enables key-based filtering for all props)

    Returns:
        bool: True if value should be rendered
    """
    # AlwaysProp: Always render, bypass all filtering
    if is_always_prop(value):
        return True

    # OptionalProp: Only render when explicitly requested
    if is_optional_prop(value):
        if partial_data:
            return value.key in partial_data
        # Never included in initial loads or standard partial reloads
        return False

    # OnceProp: Always render (client handles caching)
    if is_once_prop(value):
        # Once props are always included - the client decides whether to use cached value
        # However, respect partial_except if specified
        if partial_except:
            return value.key not in partial_except
        return True

    # LazyProp (StaticProp/DeferredProp): Only render on partial reload
    if is_lazy_prop(value):
        if partial_except:
            return value.key not in partial_except
        if partial_data:
            return value.key in partial_data
        return False

    # Regular values: Apply standard filtering
    if key is not None:
        if partial_except:
            return key not in partial_except
        if partial_data:
            return key in partial_data

    return True


def is_or_contains_lazy_prop(value: "Any") -> "bool":
    """Check if value is or contains a deferred property.

    Args:
        value: Any value to check

    Returns:
        True if value is or contains a deferred property
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


def is_or_contains_special_prop(value: "Any") -> "bool":
    """Check if value is or contains any special prop type.

    This includes lazy, once, optional, and always props.

    Args:
        value: Any value to check

    Returns:
        True if value is or contains a special prop
    """
    if is_special_prop(value):
        return True
    if isinstance(value, str):
        return False
    if isinstance(value, Mapping):
        return any(is_or_contains_special_prop(v) for v in cast("Mapping[str, Any]", value).values())
    if isinstance(value, Iterable):
        return any(is_or_contains_special_prop(v) for v in cast("Iterable[Any]", value))
    return False


def lazy_render(  # noqa: PLR0911
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

    if isinstance(value, list):
        return cast(
            "T",
            [
                lazy_render(v, partial_data, portal, partial_except)
                for v in cast("Iterable[Any]", value)
                if should_render(v, partial_data, partial_except)
            ],
        )

    if isinstance(value, tuple):
        return cast(
            "T",
            tuple(
                lazy_render(v, partial_data, portal, partial_except)
                for v in cast("Iterable[Any]", value)
                if should_render(v, partial_data, partial_except)
            ),
        )

    # Handle special prop types that need rendering
    if is_lazy_prop(value) and should_render(value, partial_data, partial_except):
        return cast("T", value.render(portal))

    if is_once_prop(value) and should_render(value, partial_data, partial_except):
        return cast("T", value.render(portal))

    if is_optional_prop(value) and should_render(value, partial_data, partial_except):
        return cast("T", value.render(portal))

    if is_always_prop(value):
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
        The shared props. Includes a special ``_once_props`` key (list of prop keys
        that were OnceProp instances) for protocol metadata generation.

    Note:
        Be sure to call this before `self.create_template_context` if you would like to include the `flash` message details.
    """
    props: "dict[str, Any]" = {}
    flash: "dict[str, list[str]]" = defaultdict(list)
    errors: "dict[str, Any]" = {}
    once_props_keys: "list[str]" = []
    error_bag = request.headers.get("X-Inertia-Error-Bag", None)

    try:
        errors = request.session.pop("_errors", {})
        shared_props = cast("dict[str,Any]", request.session.pop("_shared", {}))
        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))

        for key, value in shared_props.items():
            if not should_render(value, partial_data, partial_except, key=key):
                continue
            # Track once props for protocol metadata
            if is_once_prop(value) or (is_deferred_prop(value) and value.is_once):
                once_props_keys.append(key)
            # Render all special prop types
            if is_special_prop(value):
                props[key] = value.render(inertia_plugin.portal)
            else:
                props[key] = value

        for message in cast("list[dict[str,Any]]", request.session.pop("_messages", [])):
            flash[message["category"]].append(message["message"])

        for key, value in inertia_plugin.config.extra_static_page_props.items():
            if should_render(value, partial_data, partial_except, key=key):
                props[key] = value

        for session_prop in inertia_plugin.config.extra_session_page_props:
            if (
                session_prop not in props
                and session_prop in request.session
                and should_render(None, partial_data, partial_except, key=session_prop)
            ):
                props[session_prop] = request.session.get(session_prop)

    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to generate all shared props.  A valid session was not found for this request."
        request.logger.warning(msg)

    props["flash"] = flash
    props["errors"] = {error_bag: errors} if error_bag is not None else errors
    props["csrf_token"] = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
    # Store once props keys for later extraction (removed before serialization)
    props["_once_props"] = once_props_keys
    return props


def share(connection: "ASGIConnection[Any, Any, Any, Any]", key: "str", value: "Any") -> "bool":
    """Share a value in the session.

    Shared values are included in the props of every Inertia response for
    the current request. This is useful for data that should be available
    to all components (e.g., authenticated user, permissions, settings).

    Args:
        connection: The ASGI connection.
        key: The key to store the value under.
        value: The value to store.

    Returns:
        True if the value was successfully shared, False otherwise.
    """
    try:
        connection.session.setdefault("_shared", {}).update({key: value})
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to share value: session not accessible (user may be unauthenticated)."
        connection.logger.debug(msg)
        return False
    else:
        return True


def error(connection: "ASGIConnection[Any, Any, Any, Any]", key: "str", message: "str") -> "bool":
    """Set an error message in the session.

    Error messages are included in the ``errors`` prop of Inertia responses,
    typically used for form validation errors. The key usually corresponds
    to a form field name.

    Args:
        connection: The ASGI connection.
        key: The key to store the error under (usually a field name).
        message: The error message.

    Returns:
        True if the error was successfully stored, False otherwise.
    """
    try:
        connection.session.setdefault("_errors", {}).update({key: message})
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to set error: session not accessible (user may be unauthenticated)."
        connection.logger.debug(msg)
        return False
    else:
        return True


def flash(connection: "ASGIConnection[Any, Any, Any, Any]", message: "str", category: "str" = "info") -> "bool":
    """Add a flash message to the session.

    Flash messages are stored in the session and passed to the frontend
    via the `flash` prop in every Inertia response. They're automatically
    cleared after being displayed (pop semantics).

    This function works without requiring Litestar's FlashPlugin or
    any Jinja2 template configuration, making it ideal for SPA-only
    Inertia applications.

    Args:
        connection: The ASGI connection (Request or WebSocket).
        message: The message text to display.
        category: The message category (e.g., "success", "error", "warning", "info").
                  Defaults to "info".

    Returns:
        True if the flash message was successfully stored, False otherwise.

    Example::

        from litestar_vite.inertia import flash

        @post("/create")
        async def create_item(request: Request) -> InertiaResponse:
            flash(request, "Item created successfully!", "success")
            return InertiaResponse(...)
    """
    try:
        messages = connection.session.setdefault("_messages", [])
        messages.append({"category": category, "message": message})
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to flash message: session not accessible (user may be unauthenticated)."
        connection.logger.debug(msg)
        return False
    else:
        return True


def clear_history(connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
    """Mark that the next response should clear client history encryption keys.

    This function sets a session flag that will be consumed by the next
    InertiaResponse, causing it to include `clearHistory: true` in the page
    object. The Inertia client will then regenerate its encryption key,
    invalidating all previously encrypted history entries.

    This should typically be called during logout to ensure sensitive data
    cannot be recovered from browser history after a user logs out.

    Args:
        connection: The ASGI connection (Request).

    Note:
        Requires session middleware to be configured.
        See: https://inertiajs.com/history-encryption

    Example::

        from litestar_vite.inertia import clear_history

        @post("/logout")
        async def logout(request: Request) -> InertiaRedirect:
            request.session.clear()
            clear_history(request)
            return InertiaRedirect(request, redirect_to="/login")
    """
    try:
        connection.session["_inertia_clear_history"] = True
    except (AttributeError, ImproperlyConfiguredException):
        msg = "Unable to set clear_history flag. A valid session was not found for this request."
        connection.logger.warning(msg)


def is_pagination_container(value: "Any") -> bool:
    """Check if a value is a pagination container.

    Detects common pagination types from Litestar and Advanced Alchemy:
    - litestar.pagination.OffsetPagination (items, limit, offset, total)
    - litestar.pagination.ClassicPagination (items, page_size, current_page, total_pages)
    - advanced_alchemy.service.OffsetPagination

    Also supports any object with an `items` attribute and pagination metadata.

    Args:
        value: The value to check.

    Returns:
        True if value appears to be a pagination container.
    """
    if value is None:
        return False

    try:
        _ = value.items
    except AttributeError:
        return False

    has_offset_style = _has_offset_pagination_attrs(value)
    has_classic_style = _has_classic_pagination_attrs(value)

    return has_offset_style or has_classic_style


def extract_pagination_scroll_props(value: "Any", page_param: str = "page") -> "tuple[Any, ScrollPropsConfig | None]":
    """Extract items and scroll props from a pagination container.

    For OffsetPagination, calculates page numbers from limit/offset/total.
    For ClassicPagination, uses current_page/total_pages directly.

    Args:
        value: A pagination container (OffsetPagination, ClassicPagination, etc.).
        page_param: The query parameter name for pagination (default: "page").

    Returns:
        A tuple of (items, scroll_props) where scroll_props is None if
        value is not a pagination container.

    Example::

        items, scroll = extract_pagination_scroll_props(pagination)

        For OffsetPagination with limit=10, offset=20, total=50 the resulting scroll
        props are: ScrollPropsConfig(current_page=3, previous_page=2, next_page=4).
    """
    if not is_pagination_container(value):
        return value, None

    items = value.items

    if meta := _extract_offset_pagination_meta(value):
        current_page, previous_page, next_page = meta
        scroll_props = ScrollPropsConfig(
            page_name=page_param, current_page=current_page, previous_page=previous_page, next_page=next_page
        )
        return items, scroll_props

    if meta := _extract_classic_pagination_meta(value):
        current_page, previous_page, next_page = meta
        scroll_props = ScrollPropsConfig(
            page_name=page_param, current_page=current_page, previous_page=previous_page, next_page=next_page
        )
        return items, scroll_props

    return items, None


PAGINATION_ATTRS: tuple[tuple[str, str], ...] = (
    ("total", "total"),
    ("limit", "limit"),
    ("offset", "offset"),
    ("page_size", "pageSize"),
    ("current_page", "currentPage"),
    ("total_pages", "totalPages"),
    ("per_page", "perPage"),
    ("last_page", "lastPage"),
    ("has_more", "hasMore"),
    ("has_next", "hasNext"),
    ("has_previous", "hasPrevious"),
    ("next_cursor", "nextCursor"),
    ("previous_cursor", "previousCursor"),
)


def pagination_to_dict(value: "Any") -> dict[str, Any]:
    """Convert a pagination container to a dict with items and all metadata.

    Dynamically extracts known pagination attributes from any pagination
    container class. This supports custom pagination implementations as
    long as they have an ``items`` attribute and standard pagination metadata.

    The function checks for common pagination attributes like ``total``,
    ``limit``, ``offset`` (for offset pagination), ``page_size``, ``current_page``,
    ``total_pages`` (for classic pagination), and cursor-based attributes.
    Any found attributes are included in the result dict with camelCase keys.

    Args:
        value: A pagination container with ``items`` and metadata attributes.

    Returns:
        A dict with ``items`` and any found pagination metadata (camelCase keys).

    Example::

        from litestar.pagination import OffsetPagination

        pagination = OffsetPagination(items=[1, 2, 3], limit=10, offset=0, total=50)
        result = pagination_to_dict(pagination)

        The result contains {"items": [1, 2, 3], "total": 50, "limit": 10, "offset": 0}.

    Note:
        This function is used internally by InertiaResponse to preserve
        pagination metadata when returning pagination containers from routes.
    """
    result: dict[str, Any] = {"items": value.items}

    for attr, camel_attr in PAGINATION_ATTRS:
        try:
            attr_value = value.__getattribute__(attr)
        except AttributeError:
            continue
        result[camel_attr] = attr_value

    return result


def _has_offset_pagination_attrs(value: Any) -> bool:
    try:
        _ = value.limit
        _ = value.offset
        _ = value.total
    except AttributeError:
        return False
    return True


def _has_classic_pagination_attrs(value: Any) -> bool:
    try:
        _ = value.current_page
        _ = value.total_pages
    except AttributeError:
        return False
    return True


def _extract_offset_pagination_meta(value: Any) -> tuple[int, int | None, int | None] | None:
    try:
        limit = value.limit
        offset = value.offset
        total = value.total
    except AttributeError:
        return None

    if not (isinstance(limit, int) and isinstance(offset, int) and isinstance(total, int)):
        return None

    if limit > 0:
        current_page = (offset // limit) + 1
        total_pages = (total + limit - 1) // limit
    else:
        current_page = 1
        total_pages = 1

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    return current_page, previous_page, next_page


def _extract_classic_pagination_meta(value: Any) -> tuple[int, int | None, int | None] | None:
    try:
        current_page = value.current_page
        total_pages = value.total_pages
    except AttributeError:
        return None

    if not (isinstance(current_page, int) and isinstance(total_pages, int)):
        return None

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    return current_page, previous_page, next_page
