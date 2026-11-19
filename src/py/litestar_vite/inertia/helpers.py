"""Inertia.js v2 prop wrappers (`lazy`, `defer`, `once`, `optional`, `always`, `merge`, `scroll_props`) and state helpers."""

import inspect
import warnings
from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeGuard, TypeVar, cast, overload

from litestar.exceptions import ImproperlyConfiguredException
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState

from litestar_vite.inertia._utils import InertiaHeaders
from litestar_vite.inertia.request import build_partial_ancestors
from litestar_vite.inertia.state import (
    consume_errors,
    consume_flash,
    consume_shared,
    get_prop_eval_cache,
    peek_transient_state,
    persist_transient_state_for_redirect,
    stage_clear_history,
    stage_error,
    stage_flash,
    stage_shared,
)
from litestar_vite.inertia.types import ScrollPropsConfig

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

    from litestar_vite.inertia.plugin import InertiaPlugin


_ASYNC_RENDER_DIRECT_CALL_MSG = (
    "Async prop callback is unresolved. Async callbacks are pre-resolved on the "
    "request loop by InertiaResponse during ASGI dispatch — call render() only "
    "after the response pipeline has had a chance to await resolve_async()."
)
T = TypeVar("T")
PropKeyT = TypeVar("PropKeyT", bound=str)
StaticT = TypeVar("StaticT", bound=object)

DEFAULT_DEFERRED_GROUP = "default"


@overload
def lazy(key: str, value_or_callable: "None" = None) -> "StaticProp[str, None]": ...  # pyright: ignore[reportOverlappingOverload]


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

    Warning:
        **False Lazy Pitfall** — pass the callable reference (`lazy("data", expensive_fn)`)
        rather than invoking it eagerly (`lazy("data", expensive_fn())`).

    Args:
        key: The key to store the value under in the props dict.
        value_or_callable: Either a static value (computed eagerly, sent lazily)
            or a callable (computed and sent lazily). If None, creates a lazy
            prop with None value.

    Returns:
        StaticProp if value_or_callable is not callable, DeferredProp otherwise.

    See Also:
        - `defer`: For v2 grouped deferred props loaded after page render
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

    Example:
        ```python
        defer("permissions", lambda: Permission.all())

        defer("teams", lambda: Team.all(), group="attributes")
        defer("projects", lambda: Project.all(), group="attributes")

        defer("stats", lambda: compute_expensive_stats()).once()
        ```
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

    Example:
        ```python
        from litestar_vite.inertia import once, InertiaResponse

        @get("/dashboard", component="Dashboard")
        async def dashboard() -> InertiaResponse:
            return InertiaResponse({
                "user": current_user,
                "settings": once("settings", lambda: Settings.for_user(user_id)),
                "feature_flags": once("feature_flags", get_feature_flags()),
            })
        ```

    See Also:
        - `defer`: For deferred props that support `.once()` chaining
        - Inertia.js once props: https://inertiajs.com/partial-reloads#once
    """
    return OnceProp[str, T](key=key, value=value_or_callable)


def optional(key: str, callback: "Callable[..., T | Coroutine[Any, Any, T]]") -> "OptionalProp[str, T]":
    """Create a prop only included when explicitly requested (v2 feature).

    Optional props are NEVER included in initial page loads or standard
    partial reloads. They're only sent when the client explicitly requests
    them via `only: ['prop_name']` in a partial reload.

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

    Example:
        ```python
        from litestar.params import FromPath
        from litestar_vite.inertia import optional, InertiaResponse

        @get("/posts/{post_id}", component="Posts/Show")
        async def show_post(post_id: FromPath[int]) -> InertiaResponse:
            post = await Post.get(post_id)
            return InertiaResponse({
                "post": post,
                "comments": optional("comments", lambda: Comment.for_post(post_id)),
                "related_posts": optional("related_posts", lambda: Post.related(post_id)),
            })
        ```

        Frontend usage with `WhenVisible`:

        ```vue
        <WhenVisible data="comments" :params="{ only: ['comments'] }">
            <template #fallback>
                <LoadingSpinner />
            </template>
            <CommentList :comments="comments" />
        </WhenVisible>
        ```

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

    Example:
        ```python
        from litestar_vite.inertia import always, lazy, InertiaResponse

        @get("/dashboard", component="Dashboard")
        async def dashboard(request: Request) -> InertiaResponse:
            return InertiaResponse({
                "auth": always("auth", {"user": request.user, "can": permissions}),
                "analytics": lazy("analytics", get_analytics),
                "reports": lazy("reports", get_reports),
            })
        ```

    See Also:
        - `lazy`: For props excluded from initial load
        - `optional`: For props only included when explicitly requested
    """
    return AlwaysProp[str, T](key=key, value=value)


@dataclass
class PropFilter:
    """Configuration for prop filtering (`only` / `except_`) during partial reloads."""

    include: "set[str] | None" = None
    """Set of prop keys to explicitly include in the response."""
    exclude: "set[str] | None" = None
    """Set of prop keys to explicitly exclude from the response."""

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

    Example:
        ```python
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
        ```

    Note:
        This is a server-side helper. The client should use Inertia's
        `router.reload({ only: ['users'] })` for client-initiated filtering.
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

    Example:
        ```python
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
        ```

    Note:
        The function is named `except_` with a trailing underscore to avoid
        conflicting with Python's `except` keyword.
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
        """Return the prop key."""
        return self._key

    @property
    def value(self) -> "T":
        """Return the prop value to merge."""
        return self._value

    @property
    def strategy(self) -> "Literal['append', 'prepend', 'deep']":
        """Return the configured merge strategy (`'append'`, `'prepend'`, or `'deep'`)."""
        return self._strategy  # pyright: ignore[reportReturnType]

    @property
    def match_on(self) -> "list[str] | None":
        """Return the optional list of property keys used to deduplicate merged items."""
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

    Example:
        ```python
        merge("posts", new_posts)
        merge("messages", new_messages, strategy="prepend")
        merge("user_data", updates, strategy="deep")
        merge("posts", updated_posts, match_on="id")
        ```
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

    Example:
        ```python
        from litestar.params import FromQuery
        from litestar_vite.inertia import scroll_props, InertiaResponse

        @get("/posts", component="Posts")
        async def list_posts(page: FromQuery[int] = 1) -> InertiaResponse:
            posts = await Post.paginate(page=page, per_page=20)
            return InertiaResponse(
                {"posts": merge("posts", posts.items)},
                scroll_props=scroll_props(
                    current_page=page,
                    previous_page=page - 1 if page > 1 else None,
                    next_page=page + 1 if posts.has_more else None,
                ),
            )
        ```
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


def extract_merge_props(props: "Mapping[str, Any]") -> "tuple[list[str], list[str], list[str], list[str]]":
    """Extract merge props metadata for the Inertia v2 protocol.

    This extracts all MergeProp instances from the props dict and categorizes them
    by their merge strategy, returning the appropriate lists for the page response.

    Args:
        props: The props dictionary to scan.

    Returns:
        A tuple of (merge_props, prepend_props, deep_merge_props, match_props_on)
        where each list contains the prop keys for that strategy, and match_props_on
        is a flat list of property paths such as `items.id`.

    Example:
        ```python
        props = {
            "users": [...],
            "posts": merge("posts", new_posts),
            "messages": merge("messages", new_msgs, strategy="prepend"),
            "data": merge("data", updates, strategy="deep"),
            "items": merge("items", items, match_on="id"),
        }
        merge_props, prepend_props, deep_merge_props, match_props_on = extract_merge_props(props)
        ```

        The returned values then contain:

        - `merge_props`: `["posts", "items"]`
        - `prepend_props`: `["messages"]`
        - `deep_merge_props`: `["data"]`
        - `match_props_on`: `["items.id"]`
    """
    merge_list: "list[str]" = []
    prepend_list: "list[str]" = []
    deep_merge_list: "list[str]" = []
    match_on_paths: "list[str]" = []

    for key, value in _iter_mapping_prop_paths(props):
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
                match_on_paths.extend(f"{key}.{match_key}" for match_key in value.match_on)

    return merge_list, prepend_list, deep_merge_list, match_on_paths


def unwrap_merge_props(value: "T") -> "T":
    """Return ``value`` with any nested MergeProp wrappers replaced by their payloads."""
    if is_merge_prop(value):
        return cast("T", unwrap_merge_props(value.value))
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return cast("T", {key: unwrap_merge_props(item) for key, item in cast("Mapping[str, Any]", value).items()})
    if isinstance(value, list):
        return cast("T", [unwrap_merge_props(item) for item in cast("Iterable[Any]", value)])
    if isinstance(value, tuple):
        return cast("T", tuple(unwrap_merge_props(item) for item in cast("Iterable[Any]", value)))
    return value


class StaticProp(Generic[PropKeyT, StaticT]):
    """A wrapper for static property evaluation."""

    def __init__(self, key: "PropKeyT", value: "StaticT") -> None:
        self._key = key
        self._result = value

    @property
    def key(self) -> "PropKeyT":
        """Return the prop key."""
        return self._key

    def render(self) -> "StaticT":
        """Return the static prop value."""
        return self._result


class DeferredProp(Generic[PropKeyT, T]):
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
        """Return the prop key."""
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

        Example:
            ```python
            defer("stats", lambda: compute_expensive_stats()).once()
            ```
        """
        return DeferredProp[PropKeyT, T](key=self._key, value=self._value, group=self._group, is_once=True)

    def render(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> "T | None":
        """Evaluate and cache the deferred prop value synchronously.

        When ``cache`` is provided, stores ``(self, result)`` under ``id(self)`` without
        mutating instance attributes so shared prop objects remain isolated across requests.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return cast("T | None", cached[1])
            if self._value is None or not callable(self._value):
                result = cast("T | None", self._value)
            elif inspect.iscoroutinefunction(self._value):
                raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
            else:
                result = cast("T", self._value())
            cache[prop_id] = (self, result)
            return result
        if self._evaluated:
            return self._result
        if self._value is None or not callable(self._value):
            self._result = cast("T | None", self._value)
            self._evaluated = True
            return self._result
        if inspect.iscoroutinefunction(self._value):
            raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
        self._result = cast("T", self._value())
        self._evaluated = True
        return self._result

    async def resolve_async(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> None:
        """Pre-evaluate an async callback on the current event loop.

        No-op if already evaluated or if the callback is sync (``render()``
        handles those inline). When ``cache`` is provided, stores ``(self, result)``
        under ``id(self)`` without mutating ``_result``/``_evaluated``; otherwise
        mutates instance state so a subsequent standalone ``render()`` short-circuits.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return
            if self._value is None or not inspect.iscoroutinefunction(self._value):
                return
            result = cast("T", await self._value())
            cache[prop_id] = (self, result)
            return
        if self._evaluated:
            return
        if self._value is None or not inspect.iscoroutinefunction(self._value):
            return
        self._result = cast("T", await self._value())
        self._evaluated = True


class OnceProp(Generic[PropKeyT, T]):
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
        """Return the prop key."""
        return self._key

    def render(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> "T | None":
        """Render the prop value, caching the result.

        When ``cache`` is provided, stores ``(self, result)`` under ``id(self)`` without
        mutating instance attributes so shared prop objects remain isolated across requests.

        Returns:
            The rendered value.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return cast("T | None", cached[1])
            if not callable(self._value):
                result: "T | None" = cast("T", self._value)
            elif inspect.iscoroutinefunction(self._value):
                raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
            else:
                result = cast("T", self._value())
            cache[prop_id] = (self, result)
            return result
        if self._evaluated:
            return self._result
        if not callable(self._value):
            self._result = cast("T", self._value)
            self._evaluated = True
            return self._result
        if inspect.iscoroutinefunction(self._value):
            raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
        self._result = cast("T", self._value())
        self._evaluated = True
        return self._result

    async def resolve_async(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> None:
        """Pre-evaluate an async callback on the current event loop.

        No-op if already evaluated or if the value is not an async callback.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return
            if not callable(self._value) or not inspect.iscoroutinefunction(self._value):
                return
            result = cast("T", await self._value())
            cache[prop_id] = (self, result)
            return
        if self._evaluated:
            return
        if not callable(self._value) or not inspect.iscoroutinefunction(self._value):
            return
        self._result = cast("T", await self._value())
        self._evaluated = True


class OptionalProp(Generic[PropKeyT, T]):
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
        """Return the prop key."""
        return self._key

    def render(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> "T | None":
        """Render the prop value, caching the result.

        When ``cache`` is provided, stores ``(self, result)`` under ``id(self)`` without
        mutating instance attributes so shared prop objects remain isolated across requests.

        Returns:
            The rendered value.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return cast("T | None", cached[1])
            if inspect.iscoroutinefunction(self._callback):
                raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
            result = cast("T", self._callback())
            cache[prop_id] = (self, result)
            return result
        if self._evaluated:
            return self._result
        if inspect.iscoroutinefunction(self._callback):
            raise RuntimeError(_ASYNC_RENDER_DIRECT_CALL_MSG)
        self._result = cast("T", self._callback())
        self._evaluated = True
        return self._result

    async def resolve_async(self, *, cache: "dict[int, tuple[Any, Any]] | None" = None) -> None:
        """Pre-evaluate an async callback on the current event loop.

        No-op if already evaluated or if the callback is sync.
        """
        if cache is not None:
            prop_id = id(self)
            cached = cache.get(prop_id)
            if cached is not None and cached[0] is self:
                return
            if not inspect.iscoroutinefunction(self._callback):
                return
            result = cast("T", await self._callback())
            cache[prop_id] = (self, result)
            return
        if self._evaluated:
            return
        if not inspect.iscoroutinefunction(self._callback):
            return
        self._result = cast("T", await self._callback())
        self._evaluated = True


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
        """Return the prop key."""
        return self._key

    @property
    def value(self) -> "T":
        """Return the eagerly evaluated prop value."""
        return self._value

    def render(self) -> "T":
        """Return the prop value.

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


def extract_deferred_props(props: "Mapping[str, Any]") -> "dict[str, list[str]]":
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

    Example:
        ```python
        props = {
            "users": [...],
            "teams": defer("teams", get_teams, group="attributes"),
            "projects": defer("projects", get_projects, group="attributes"),
            "permissions": defer("permissions", get_permissions),
        }
        result = extract_deferred_props(props)
        ```

        The result is `{"default": ["permissions"], "attributes": ["teams", "projects"]}`.
    """
    groups: "dict[str, list[str]]" = {}

    for key, value in _iter_mapping_prop_paths(props):
        if is_deferred_prop(value):
            if value.is_once:
                continue
            group = value.group
            if group not in groups:
                groups[group] = []
            groups[group].append(key)

    return groups


def extract_once_props(
    props: "Mapping[str, Any]", partial_data: "set[str] | None" = None, partial_except: "set[str] | None" = None
) -> "list[str]":
    """Extract once props for the Inertia v2.2.20+ protocol.

    Once props are cached client-side after first resolution. This function
    extracts all OnceProp instances and DeferredProp instances with is_once=True.

    Args:
        props: The props dictionary to scan.
        partial_data: Optional set of requested partial prop keys.
        partial_except: Optional set of prop keys excluded from the partial response.

    Returns:
        A list of prop keys that should be cached client-side.
        Empty list if no once props found.

    Example:
        ```python
        props = {
            "user": current_user,
            "settings": once("settings", get_settings),
            "stats": defer("stats", get_stats).once(),
        }
        result = extract_once_props(props)
        ```

        The result is `["settings", "stats"]`.
    """
    return [key for key, _ in _extract_once_prop_entries(props, partial_data, partial_except)]


def build_once_props_metadata(keys: "Iterable[str | _OncePropEntry]") -> "dict[str, dict[str, str | int | None]]":
    """Build stable once-prop metadata for the Inertia page object."""
    metadata: "dict[str, dict[str, str | int | None]]" = {}
    for item in keys:
        key, prop = item if isinstance(item, tuple) else (item, item)
        metadata[key] = {"prop": prop}
    return metadata


def should_render(  # noqa: PLR0911
    value: "Any",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    key: "str | None" = None,
    _partial_data_ancestors: "frozenset[str] | None" = None,
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
        except_once_props: Optional set of once-prop keys already cached client-side.
        key: Optional key name for this prop (enables key-based filtering for all props)
        _partial_data_ancestors: Optional precomputed ancestor prefixes for ``partial_data``.

    Returns:
        bool: True if value should be rendered
    """
    if is_always_prop(value):
        return True

    if is_optional_prop(value):
        if partial_data and not _matches_partial_data(value, partial_data, key, _partial_data_ancestors):
            return False
        if partial_except and _matches_partial_except(value, partial_except, key):
            return False
        return not (not partial_data and not partial_except)

    if is_once_prop(value):
        if partial_data and not _matches_partial_data(value, partial_data, key, _partial_data_ancestors):
            return False
        if partial_except and _matches_partial_except(value, partial_except, key):
            return False
        if not partial_data and not partial_except and except_once_props:
            return not _matches_partial_except(value, except_once_props, key)
        return True

    if is_lazy_prop(value):
        if partial_data and not _matches_partial_data(value, partial_data, key, _partial_data_ancestors):
            return False
        if partial_except and _matches_partial_except(value, partial_except, key):
            return False
        return not (not partial_data and not partial_except)

    if key is not None:
        if partial_data and not _matches_partial_data(value, partial_data, key, _partial_data_ancestors):
            return False
        if partial_except and _matches_partial_except(value, partial_except, key):
            return False

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


def _is_async_special_prop(value: "DeferredProp[Any, Any] | OnceProp[Any, Any] | OptionalProp[Any, Any]") -> bool:
    if isinstance(value, OptionalProp):
        return inspect.iscoroutinefunction(value._callback)  # pyright: ignore[reportPrivateUsage]
    cb = value._value  # pyright: ignore[reportPrivateUsage]
    return callable(cb) and inspect.iscoroutinefunction(cb)


def _is_prop_evaluated(
    value: "DeferredProp[Any, Any] | OnceProp[Any, Any] | OptionalProp[Any, Any]",
    eval_cache: "dict[int, tuple[Any, Any]] | None",
) -> bool:
    if eval_cache is not None:
        cached = eval_cache.get(id(value))
        return cached is not None and cached[0] is value
    return value._evaluated  # pyright: ignore[reportPrivateUsage]


def _render_special_prop(
    value: "Any", eval_cache: "dict[int, tuple[Any, Any]] | None" = None, *, allow_instance_async_result: bool = False
) -> "Any":
    if is_deferred_prop(value) or is_once_prop(value) or is_optional_prop(value):
        if (
            allow_instance_async_result
            and eval_cache is not None
            and _is_async_special_prop(value)
            and value._evaluated  # pyright: ignore[reportPrivateUsage]
        ):
            cached = eval_cache.get(id(value))
            if cached is None or cached[0] is not value:
                return value.render()
        return value.render(cache=eval_cache)
    if is_lazy_prop(value) or is_always_prop(value):
        return value.render()
    return value


def _lazy_render_sequence_mapping(
    mapping: "Mapping[str, Any]",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    ancestors: "frozenset[str] | None",
    eval_cache: "dict[int, tuple[Any, Any]]",
    allow_instance_async_result: bool = False,
) -> "dict[str, Any]":
    rendered: "dict[str, Any]" = {}
    for k, v in mapping.items():
        if is_special_prop(v):
            if should_render(v, partial_data, partial_except, except_once_props, _partial_data_ancestors=ancestors):
                rendered[k] = _render_special_prop(
                    v, eval_cache, allow_instance_async_result=allow_instance_async_result
                )
        elif isinstance(v, Mapping):
            rendered[k] = (
                _lazy_render_sequence_mapping(
                    cast("Mapping[str, Any]", v),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                )
                if is_or_contains_special_prop(v)
                else v
            )
        elif isinstance(v, list):
            rendered[k] = _lazy_render_sequence(
                cast("Iterable[Any]", v),
                partial_data,
                partial_except,
                except_once_props,
                ancestors,
                eval_cache,
                allow_instance_async_result,
            )
        elif isinstance(v, tuple):
            rendered[k] = tuple(
                _lazy_render_sequence(
                    cast("Iterable[Any]", v),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                )
            )
        else:
            rendered[k] = v
    return rendered


def _lazy_render_sequence(
    sequence: "Iterable[Any]",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    ancestors: "frozenset[str] | None",
    eval_cache: "dict[int, tuple[Any, Any]]",
    allow_instance_async_result: bool = False,
) -> "list[Any]":
    rendered: "list[Any]" = []
    for v in sequence:
        if is_special_prop(v):
            if should_render(v, partial_data, partial_except, except_once_props, _partial_data_ancestors=ancestors):
                rendered.append(
                    _render_special_prop(v, eval_cache, allow_instance_async_result=allow_instance_async_result)
                )
        elif isinstance(v, Mapping):
            rendered.append(
                _lazy_render_sequence_mapping(
                    cast("Mapping[str, Any]", v),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                )
                if is_or_contains_special_prop(v)
                else v
            )
        elif isinstance(v, list):
            rendered.append(
                _lazy_render_sequence(
                    cast("Iterable[Any]", v),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                )
            )
        elif isinstance(v, tuple):
            rendered.append(
                tuple(
                    _lazy_render_sequence(
                        cast("Iterable[Any]", v),
                        partial_data,
                        partial_except,
                        except_once_props,
                        ancestors,
                        eval_cache,
                        allow_instance_async_result,
                    )
                )
            )
        else:
            rendered.append(v)
    return rendered


def _has_unresolved_in_sequence(
    items: "Iterable[Any]",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    ancestors: "frozenset[str] | None",
    eval_cache: "dict[int, tuple[Any, Any]] | None",
) -> bool:
    for v in items:
        if is_special_prop(v):
            if has_unresolved_async_props(
                v,
                partial_data=partial_data,
                partial_except=partial_except,
                except_once_props=except_once_props,
                _partial_data_ancestors=ancestors,
                _in_sequence=True,
                _eval_cache=eval_cache,
            ):
                return True
        elif isinstance(v, Mapping):
            if is_or_contains_special_prop(v) and has_unresolved_async_props(
                v,
                partial_data=partial_data,
                partial_except=partial_except,
                except_once_props=except_once_props,
                _partial_data_ancestors=ancestors,
                _in_sequence=True,
                _eval_cache=eval_cache,
            ):
                return True
        elif isinstance(v, (list, tuple)) and has_unresolved_async_props(
            v,
            partial_data=partial_data,
            partial_except=partial_except,
            except_once_props=except_once_props,
            _partial_data_ancestors=ancestors,
            _in_sequence=True,
            _eval_cache=eval_cache,
        ):
            return True
    return False


async def _resolve_async_in_sequence(
    items: "Iterable[Any]",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    ancestors: "frozenset[str] | None",
    eval_cache: "dict[int, tuple[Any, Any]] | None",
) -> None:
    for v in items:
        if is_special_prop(v):
            if should_render(v, partial_data, partial_except, except_once_props, _partial_data_ancestors=ancestors):
                await _resolve_one(v, partial_data, partial_except, except_once_props, None, ancestors, eval_cache)
        elif isinstance(v, Mapping):
            if is_or_contains_special_prop(v):
                await resolve_async_props(
                    v,
                    partial_data=partial_data,
                    partial_except=partial_except,
                    except_once_props=except_once_props,
                    _partial_data_ancestors=ancestors,
                    _in_sequence=True,
                    _eval_cache=eval_cache,
                )
        elif isinstance(v, (list, tuple)):
            await resolve_async_props(
                v,
                partial_data=partial_data,
                partial_except=partial_except,
                except_once_props=except_once_props,
                _partial_data_ancestors=ancestors,
                _in_sequence=True,
                _eval_cache=eval_cache,
            )


def _lazy_render(  # noqa: PLR0911
    value: "T",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    key: "str | None",
    ancestors: "frozenset[str] | None",
    in_sequence: bool,
    eval_cache: "dict[int, tuple[Any, Any]]",
    allow_instance_async_result: bool,
) -> "T":
    if isinstance(value, str):
        return cast("T", value)
    if isinstance(value, Mapping):
        if in_sequence:
            return cast(
                "T",
                _lazy_render_sequence_mapping(
                    cast("Mapping[str, Any]", value),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                ),
            )
        rendered: "dict[str, Any]" = {}
        for k, v in cast("Mapping[str, Any]", value).items():
            child_key = _join_prop_path((str(k),)) if key is None else f"{key}.{k}"
            if isinstance(v, Mapping):
                child: Any = _lazy_render(
                    cast("Mapping[str, Any]", v),
                    partial_data,
                    partial_except,
                    except_once_props,
                    child_key,
                    ancestors,
                    False,
                    eval_cache,
                    allow_instance_async_result,
                )
                if (
                    should_render(
                        v,
                        partial_data,
                        partial_except,
                        except_once_props,
                        key=child_key,
                        _partial_data_ancestors=ancestors,
                    )
                    or child
                ):
                    rendered[k] = child
                continue
            if should_render(
                v, partial_data, partial_except, except_once_props, key=child_key, _partial_data_ancestors=ancestors
            ):
                rendered[k] = _lazy_render(
                    v,
                    partial_data,
                    partial_except,
                    except_once_props,
                    child_key,
                    ancestors,
                    False,
                    eval_cache,
                    allow_instance_async_result,
                )
        return cast("T", rendered)

    if isinstance(value, list):
        return cast(
            "T",
            _lazy_render_sequence(
                cast("Iterable[Any]", value),
                partial_data,
                partial_except,
                except_once_props,
                ancestors,
                eval_cache,
                allow_instance_async_result,
            ),
        )

    if isinstance(value, tuple):
        return cast(
            "T",
            tuple(
                _lazy_render_sequence(
                    cast("Iterable[Any]", value),
                    partial_data,
                    partial_except,
                    except_once_props,
                    ancestors,
                    eval_cache,
                    allow_instance_async_result,
                )
            ),
        )

    if is_lazy_prop(value) and should_render(
        value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
    ):
        return cast(
            "T", _render_special_prop(value, eval_cache, allow_instance_async_result=allow_instance_async_result)
        )

    if is_once_prop(value) and should_render(
        value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
    ):
        return cast(
            "T", _render_special_prop(value, eval_cache, allow_instance_async_result=allow_instance_async_result)
        )

    if is_optional_prop(value) and should_render(
        value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
    ):
        return cast(
            "T", _render_special_prop(value, eval_cache, allow_instance_async_result=allow_instance_async_result)
        )

    if is_always_prop(value):
        return cast("T", value.render())

    return cast("T", value)


def lazy_render(
    value: "T",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    _key: "str | None" = None,
    _partial_data_ancestors: "frozenset[str] | None" = None,
    _in_sequence: bool = False,
    _eval_cache: "dict[int, tuple[Any, Any]] | None" = None,
) -> "T":
    """Filter deferred properties from the value based on partial data.

    For v2 protocol, partial_except takes precedence over partial_data.

    Async-callback props must be pre-resolved by `resolve_async_props`
    before this function runs; otherwise their `render` will raise.

    Args:
        value: The value to filter
        partial_data: Keys to include (X-Inertia-Partial-Data)
        partial_except: Keys to exclude (X-Inertia-Partial-Except, v2)
        except_once_props: Cached once-prop keys to omit when possible.
        _key: Internal dot-path prefix for recursive mapping traversal.
        _partial_data_ancestors: Optional precomputed ancestor prefixes for ``partial_data``.
        _in_sequence: Internal flag preserving plain dict keys inside sequences.
        _eval_cache: Optional per-request evaluation cache keyed by ``id(prop)``.

    Returns:
        The filtered value
    """
    ancestors = (
        build_partial_ancestors(partial_data)
        if partial_data and _partial_data_ancestors is None
        else _partial_data_ancestors
    )
    allow_instance_async_result = _eval_cache is None
    eval_cache: "dict[int, tuple[Any, Any]]" = {} if _eval_cache is None else _eval_cache
    return _lazy_render(
        value,
        partial_data,
        partial_except,
        except_once_props,
        _key,
        ancestors,
        _in_sequence,
        eval_cache,
        allow_instance_async_result,
    )


def has_unresolved_async_props(  # noqa: PLR0911
    value: "Any",
    *,
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    _key: "str | None" = None,
    _partial_data_ancestors: "frozenset[str] | None" = None,
    _in_sequence: bool = False,
    _eval_cache: "dict[int, tuple[Any, Any]] | None" = None,
) -> bool:
    """Return ``True`` if ``value`` (recursively) contains a prop that will be
    rendered for this request AND whose async callback hasn't been evaluated yet.

    Mirrors `should_render` filtering so out-of-scope props (an
    ``optional()`` on a full page load, a ``defer()`` not in ``partial_data``)
    don't count — preserving the laziness contract and preventing infinite
    re-deferral when ``InertiaResponse.to_asgi_response`` re-enters after
    async resolution populates the evaluation cache.
    """
    ancestors = (
        build_partial_ancestors(partial_data)
        if partial_data and _partial_data_ancestors is None
        else _partial_data_ancestors
    )
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, Any]", value)
        if _in_sequence:
            return _has_unresolved_in_sequence(
                mapping.values(), partial_data, partial_except, except_once_props, ancestors, _eval_cache
            )
        for k, v in mapping.items():
            child_key = _join_prop_path((str(k),)) if _key is None else f"{_key}.{k}"
            if isinstance(v, Mapping):
                if has_unresolved_async_props(
                    v,
                    partial_data=partial_data,
                    partial_except=partial_except,
                    except_once_props=except_once_props,
                    _key=child_key,
                    _partial_data_ancestors=ancestors,
                    _eval_cache=_eval_cache,
                ):
                    return True
                continue
            if not should_render(
                v, partial_data, partial_except, except_once_props, key=child_key, _partial_data_ancestors=ancestors
            ):
                continue
            if has_unresolved_async_props(
                v,
                partial_data=partial_data,
                partial_except=partial_except,
                except_once_props=except_once_props,
                _key=child_key,
                _partial_data_ancestors=ancestors,
                _eval_cache=_eval_cache,
            ):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return _has_unresolved_in_sequence(
            cast("Iterable[Any]", value), partial_data, partial_except, except_once_props, ancestors, _eval_cache
        )
    if not should_render(
        value, partial_data, partial_except, except_once_props, key=_key, _partial_data_ancestors=ancestors
    ):
        return False
    if is_optional_prop(value):
        return not _is_prop_evaluated(value, _eval_cache) and inspect.iscoroutinefunction(
            value._callback  # pyright: ignore[reportPrivateUsage]
        )
    if is_deferred_prop(value):
        cb = value._value  # pyright: ignore[reportPrivateUsage]
        return not _is_prop_evaluated(value, _eval_cache) and cb is not None and inspect.iscoroutinefunction(cb)
    if is_once_prop(value):
        cb = value._value  # pyright: ignore[reportPrivateUsage]
        return not _is_prop_evaluated(value, _eval_cache) and callable(cb) and inspect.iscoroutinefunction(cb)
    return False


async def resolve_async_props(
    value: "Any",
    *,
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    _key: "str | None" = None,
    _partial_data_ancestors: "frozenset[str] | None" = None,
    _in_sequence: bool = False,
    _eval_cache: "dict[int, tuple[Any, Any]] | None" = None,
) -> None:
    """Walk ``value`` and ``await`` async prop callbacks on the current loop.

    Mirrors the filter logic of `lazy_render` so we only evaluate props
    that will actually be rendered for this request — preserving the laziness
    contract of ``defer()``/``optional()`` on full page loads.

    When ``_eval_cache`` is provided, stores resolved values in the per-request
    cache without mutating `DeferredProp`, `OnceProp`, or `OptionalProp`
    instances. Sync callbacks and already-evaluated props are left untouched.

    Args:
        value: The response content (typically a ``dict``).
        partial_data: ``X-Inertia-Partial-Data`` keys, when present.
        partial_except: ``X-Inertia-Partial-Except`` keys (v2 protocol).
        except_once_props: Once-prop keys cached client-side.
        _key: Internal dot-path prefix for recursive mapping traversal.
        _partial_data_ancestors: Optional precomputed ancestor prefixes for ``partial_data``.
        _in_sequence: Internal flag preserving plain dict keys inside sequences.
        _eval_cache: Optional per-request evaluation cache keyed by ``id(prop)``.
    """
    ancestors = (
        build_partial_ancestors(partial_data)
        if partial_data and _partial_data_ancestors is None
        else _partial_data_ancestors
    )
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, Any]", value)
        if _in_sequence:
            await _resolve_async_in_sequence(
                mapping.values(), partial_data, partial_except, except_once_props, ancestors, _eval_cache
            )
            return
        for k, v in mapping.items():
            child_key = _join_prop_path((str(k),)) if _key is None else f"{_key}.{k}"
            if isinstance(v, Mapping):
                await resolve_async_props(
                    v,
                    partial_data=partial_data,
                    partial_except=partial_except,
                    except_once_props=except_once_props,
                    _key=child_key,
                    _partial_data_ancestors=ancestors,
                    _eval_cache=_eval_cache,
                )
                continue
            if not should_render(
                v, partial_data, partial_except, except_once_props, key=child_key, _partial_data_ancestors=ancestors
            ):
                continue
            await _resolve_one(v, partial_data, partial_except, except_once_props, child_key, ancestors, _eval_cache)
        return

    if isinstance(value, (list, tuple)):
        await _resolve_async_in_sequence(
            cast("Iterable[Any]", value), partial_data, partial_except, except_once_props, ancestors, _eval_cache
        )
        return

    await _resolve_one(value, partial_data, partial_except, except_once_props, _key, ancestors, _eval_cache)


def get_raw_shared_props(request: "ASGIConnection[Any, Any, Any, Any]") -> "Mapping[str, Any]":
    """Return the unrendered shared props stored on the request session.

    ``get_shared_props()`` consumes and renders ``_shared``. Callers that need
    deferred metadata or async pre-resolution must inspect the raw mapping
    before that happens.
    """
    try:
        shared_props = request.session.get("_shared", {})
    except (AttributeError, ImproperlyConfiguredException):
        shared_props = {}
    session_shared: Mapping[str, Any] = (
        cast("Mapping[str, Any]", shared_props) if isinstance(shared_props, Mapping) else {}
    )
    state = peek_transient_state(request)
    return {**session_shared, **(state.shared if state is not None else {})}


def _consume_session_handoff_state(
    request: "ASGIConnection[Any, Any, Any, Any]",
) -> "tuple[dict[str, Any] | None, Mapping[str, Any], dict[str, Any], list[dict[str, Any]]]":
    try:
        session = request.session
        raw_shared: Any = session.pop("_shared", {})
        raw_errors: Any = session.pop("_errors", {})
        raw_messages: Any = session.pop("_messages", [])
    except (AttributeError, ImproperlyConfiguredException):
        return None, {}, {}, []

    shared: Mapping[str, Any] = cast("Mapping[str, Any]", raw_shared) if isinstance(raw_shared, Mapping) else {}
    errors = dict(cast("Mapping[str, Any]", raw_errors)) if isinstance(raw_errors, Mapping) else {}
    messages = cast("list[dict[str, Any]]", raw_messages) if isinstance(raw_messages, list) else []
    return session, shared, errors, messages


def _merge_filtered_props(
    target: "dict[str, Any]",
    source: "Mapping[str, Any]",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    ancestors: "frozenset[str] | None",
    eval_cache: "dict[int, tuple[Any, Any]]",
    *,
    render_plain_mappings: bool,
) -> None:
    for key, value in source.items():
        if isinstance(value, Mapping):
            if render_plain_mappings or is_or_contains_special_prop(value):
                rendered: Any = lazy_render(
                    cast("Mapping[str, Any]", value),
                    partial_data,
                    partial_except,
                    except_once_props,
                    _key=key,
                    _partial_data_ancestors=ancestors,
                    _eval_cache=eval_cache,
                )
                if rendered or should_render(
                    value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
                ):
                    target[key] = rendered
            elif should_render(
                value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
            ):
                target[key] = value
            continue
        if not should_render(
            value, partial_data, partial_except, except_once_props, key=key, _partial_data_ancestors=ancestors
        ):
            continue
        if is_special_prop(value):
            target[key] = _render_special_prop(value, eval_cache)
        elif is_or_contains_special_prop(value):
            target[key] = lazy_render(
                value,
                partial_data,
                partial_except,
                except_once_props,
                _key=key,
                _partial_data_ancestors=ancestors,
                _eval_cache=eval_cache,
            )
        else:
            target[key] = value


def get_shared_props(
    request: "ASGIConnection[Any, Any, Any, Any]",
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    _partial_data_ancestors: "frozenset[str] | None" = None,
    _eval_cache: "dict[int, tuple[Any, Any]] | None" = None,
) -> "dict[str, Any]":
    """Return shared session props for a request.

    For v2 protocol, partial_except takes precedence over partial_data.

    Args:
        request: The ASGI connection.
        partial_data: Optional set of keys to include (X-Inertia-Partial-Data).
        partial_except: Optional set of keys to exclude (X-Inertia-Partial-Except, v2).
        except_once_props: Optional cached once-prop keys sent by the client.
        _partial_data_ancestors: Optional precomputed ancestor prefixes for ``partial_data``.
        _eval_cache: Optional per-request evaluation cache keyed by ``id(prop)``.

    Returns:
        The shared props. Includes a special ``_once_props`` key (list of prop keys
        that were OnceProp instances) for protocol metadata generation.

    Note:
        Be sure to call this before `self.create_template_context` if you would like to include the `flash` message details.
    """
    ancestors = (
        build_partial_ancestors(partial_data)
        if partial_data and _partial_data_ancestors is None
        else _partial_data_ancestors
    )
    eval_cache = get_prop_eval_cache(request) if _eval_cache is None else _eval_cache
    props: "dict[str, Any]" = {}
    flash: "dict[str, list[str]]" = defaultdict(list)
    once_props_entries: "list[_OncePropEntry]" = []
    error_bag = request.headers.get(InertiaHeaders.ERROR_BAG.value, None)

    session, session_shared_props, errors, session_messages = _consume_session_handoff_state(request)
    local_shared_props = consume_shared(request)
    local_flash = consume_flash(request)
    local_errors = consume_errors(request)
    errors.update(local_errors)
    shared_props = {**session_shared_props, **local_shared_props}

    try:
        inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))

        once_props_entries = _extract_once_prop_entries(shared_props, partial_data, partial_except)
        if inertia_plugin.config.extra_static_page_props:
            once_props_entries.extend(
                _extract_once_prop_entries(inertia_plugin.config.extra_static_page_props, partial_data, partial_except)
            )

        _merge_filtered_props(
            props,
            shared_props,
            partial_data,
            partial_except,
            except_once_props,
            ancestors,
            eval_cache,
            render_plain_mappings=True,
        )

        for message in session_messages:
            flash[message["category"]].append(message["message"])
        for category, messages in local_flash.items():
            flash[category].extend(messages)

        _merge_filtered_props(
            props,
            inertia_plugin.config.extra_static_page_props,
            partial_data,
            partial_except,
            except_once_props,
            ancestors,
            eval_cache,
            render_plain_mappings=False,
        )

        if session is not None:
            for session_prop in inertia_plugin.config.extra_session_page_props:
                if (
                    session_prop not in props
                    and session_prop in session
                    and should_render(
                        None, partial_data, partial_except, key=session_prop, _partial_data_ancestors=ancestors
                    )
                ):
                    props[session_prop] = session.get(session_prop)

    except (AttributeError, ImproperlyConfiguredException, KeyError):
        pass

    props["flash"] = flash
    props["errors"] = {error_bag: errors} if error_bag is not None else errors
    props["csrf_token"] = value_or_default(ScopeState.from_scope(request.scope).csrf_token, "")
    props["_once_props"] = once_props_entries
    return props


_UNMATERIALIZABLE_SHARED = object()


def _materialize_shared_value(  # pyright: ignore[reportUnusedFunction]
    value: "Any", *, cache: "dict[int, tuple[Any, Any]] | None" = None
) -> "Any":
    """Convert top-level special props into session-serializable values for share().

    Called by ``inertia.state.persist_transient_state_for_redirect`` via a function-local
    import, so static analysers report it as unused.

    Args:
        value: A staged shared prop value.
        cache: Optional per-request evaluation cache keyed by ``id(prop)``.

    Returns:
        A session-serializable value, or ``_UNMATERIALIZABLE_SHARED`` when the value cannot
        be resolved outside a live request.
    """
    if is_merge_prop(value):
        return unwrap_merge_props(value)
    if is_special_prop(value):
        try:
            return _render_special_prop(value, cache)
        except RuntimeError:
            return _UNMATERIALIZABLE_SHARED
    return value


def materialize_shared_props_to_session(connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
    """Persist staged Inertia state through the compatibility session handoff.

    Deprecated:
        This compatibility shim will be removed in v0.30.0. Redirect responses
        persist transient state automatically.

    Args:
        connection: The current ASGI connection.
    """
    warnings.warn(
        "materialize_shared_props_to_session() is deprecated and will be removed in v0.30.0; "
        "redirect responses persist transient Inertia state automatically.",
        DeprecationWarning,
        stacklevel=2,
    )
    persist_transient_state_for_redirect(connection)


def share(connection: "ASGIConnection[Any, Any, Any, Any]", key: "str", value: "Any") -> "bool":
    """Stage a shared value for the current Inertia response.

    Shared values are included in the props of every Inertia response for
    the current request. This is useful for data that should be available
    to all components (e.g., authenticated user, permissions, settings).
    Top-level special props remain raw in request scope and are materialized lazily in the
    handler frame only when the response includes them. Redirect responses persist supported
    synchronous values when the request exposes a session transport. Async special props remain
    available to the current response but cannot cross a redirect.

    Args:
        connection: The ASGI connection.
        key: The key to store the value under.
        value: The value to store.

    Returns:
        True when the value was staged for the current request.
    """
    stage_shared(connection, key, value)
    return True


def error(connection: "ASGIConnection[Any, Any, Any, Any]", key: "str", message: "str") -> "bool":
    """Stage an error message for the current Inertia response.

    Error messages are included in the ``errors`` prop of Inertia responses,
    typically used for form validation errors. The key usually corresponds
    to a form field name.

    Args:
        connection: The ASGI connection.
        key: The key to store the error under (usually a field name).
        message: The error message.

    Returns:
        True when the error was staged for the current request.
    """
    stage_error(connection, key, message)
    return True


def flash(connection: "ASGIConnection[Any, Any, Any, Any]", message: "str", category: "str" = "info") -> "bool":
    """Stage a flash message for the current Inertia response.

    Flash messages are consumed into the top-level ``flash`` page field. Redirect responses
    persist them when the request exposes a session transport.

    This function works without requiring Litestar's FlashPlugin or
    any Jinja2 template configuration, making it ideal for SPA-only
    Inertia applications.

    Args:
        connection: The ASGI connection (Request or WebSocket).
        message: The message text to display.
        category: The message category (e.g., "success", "error", "warning", "info").
                  Defaults to "info".

    Returns:
        True when the flash message was staged for the current request.

    Example:
        ```python
        from litestar_vite.inertia import flash

        @post("/create")
        async def create_item(request: Request) -> InertiaResponse:
            flash(request, "Item created successfully!", "success")
            return InertiaResponse(...)
        ```
    """
    stage_flash(connection, message, category)
    return True


def clear_history(connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
    """Mark that the next response should clear client history encryption keys.

    This function stages a request-local flag consumed by the current
    InertiaResponse. Redirect responses persist the flag when the request
    exposes a session transport.

    This should typically be called during logout to ensure sensitive data
    cannot be recovered from browser history after a user logs out.

    Args:
        connection: The ASGI connection (Request).

    Example:
        ```python
        from litestar_vite.inertia import clear_history

        @post("/logout")
        async def logout(request: Request) -> InertiaRedirect:
            request.session.clear()
            clear_history(request)
            return InertiaRedirect(request, redirect_to="/login")
        ```
    """
    stage_clear_history(connection)


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

    Example:
        ```python
        items, scroll = extract_pagination_scroll_props(pagination)
        ```

        For `OffsetPagination` with `limit=10, offset=20, total=50` the resulting scroll
        props are `ScrollPropsConfig(current_page=3, previous_page=2, next_page=4)`.
    """
    if not is_pagination_container(value):
        return value, None

    items = value.items

    if meta := (_extract_offset_pagination_meta(value) or _extract_classic_pagination_meta(value)):
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
    long as they have an `items` attribute and standard pagination metadata.

    The function checks for common pagination attributes like `total`,
    `limit`, `offset` (for offset pagination), `page_size`, `current_page`,
    `total_pages` (for classic pagination), and cursor-based attributes.
    Any found attributes are included in the result dict with camelCase keys.

    Args:
        value: A pagination container with `items` and metadata attributes.

    Returns:
        A dict with `items` and any found pagination metadata (camelCase keys).

    Example:
        ```python
        from litestar.pagination import OffsetPagination

        pagination = OffsetPagination(items=[1, 2, 3], limit=10, offset=0, total=50)
        result = pagination_to_dict(pagination)
        ```

        The result contains `{"items": [1, 2, 3], "total": 50, "limit": 10, "offset": 0}`.

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


_OncePropEntry = tuple[str, str]


def _join_prop_path(path: "tuple[str, ...]") -> str:
    return ".".join(path)


def _iter_mapping_prop_paths(value: "Mapping[str, Any]", path: "tuple[str, ...]" = ()) -> "Iterator[tuple[str, Any]]":
    for key, item in value.items():
        item_path = (*path, str(key))
        yield _join_prop_path(item_path), item
        if isinstance(item, Mapping):
            yield from _iter_mapping_prop_paths(cast("Mapping[str, Any]", item), item_path)


def _prop_key_candidates(value: "Any", key: "str | None") -> "tuple[str, ...]":
    candidates: "list[str]" = []
    if key:
        candidates.append(key)
        local_key = key.rsplit(".", maxsplit=1)[-1]
        if local_key != key:
            candidates.append(local_key)
    prop_key = getattr(value, "key", None)
    if isinstance(prop_key, str):
        candidates.append(prop_key)
    return tuple(dict.fromkeys(candidates))


def _has_excluded_ancestor(candidate: str, partial_except: "set[str]") -> bool:
    idx = candidate.find(".")
    while idx != -1:
        if candidate[:idx] in partial_except:
            return True
        idx = candidate.find(".", idx + 1)
    return False


def _matches_partial_data(
    value: "Any", partial_data: "set[str]", key: "str | None", ancestors: "frozenset[str] | None" = None
) -> bool:
    candidates = _prop_key_candidates(value, key)
    if is_special_prop(value):
        return any(candidate in partial_data for candidate in candidates)
    effective_ancestors = build_partial_ancestors(partial_data) if ancestors is None else ancestors
    return any(candidate in partial_data or candidate in effective_ancestors for candidate in candidates)


def _matches_partial_except(value: "Any", partial_except: "set[str]", key: "str | None") -> bool:
    candidates = _prop_key_candidates(value, key)
    return any(
        candidate in partial_except or _has_excluded_ancestor(candidate, partial_except) for candidate in candidates
    )


def _should_track_once_prop(
    key: str,
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    prop_path: "str | None" = None,
) -> bool:
    """Return whether once-prop metadata should stay in scope for this response."""
    candidates = tuple(dict.fromkeys((key, prop_path or key)))
    if partial_except:
        return not any(candidate in partial_except for candidate in candidates)
    if partial_data:
        return any(candidate in partial_data for candidate in candidates)
    return True


def _extract_once_prop_entries(
    props: "Mapping[str, Any]", partial_data: "set[str] | None" = None, partial_except: "set[str] | None" = None
) -> "list[_OncePropEntry]":
    entries: "list[_OncePropEntry]" = []

    for prop_path, value in _iter_mapping_prop_paths(props):
        if is_once_prop(value) or (is_deferred_prop(value) and value.is_once):
            key = str(value.key)
            if _should_track_once_prop(key, partial_data, partial_except, prop_path):
                entries.append((key, prop_path))

    return entries


async def _resolve_one(
    value: "Any",
    partial_data: "set[str] | None",
    partial_except: "set[str] | None",
    except_once_props: "set[str] | None",
    key: "str | None",
    ancestors: "frozenset[str] | None" = None,
    eval_cache: "dict[int, tuple[Any, Any]] | None" = None,
) -> None:
    if is_optional_prop(value) or is_deferred_prop(value) or is_once_prop(value):
        await value.resolve_async(cache=eval_cache)
        return
    if isinstance(value, (Mapping, list, tuple)):
        await resolve_async_props(
            value,
            partial_data=partial_data,
            partial_except=partial_except,
            except_once_props=except_once_props,
            _key=key,
            _partial_data_ancestors=ancestors,
            _eval_cache=eval_cache,
        )


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
