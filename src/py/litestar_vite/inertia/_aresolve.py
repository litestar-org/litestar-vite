"""Async pre-resolution of Inertia prop callbacks on the request loop.

The portal-based path in :mod:`litestar_vite.inertia._async_mixin` runs async
callbacks on a dedicated thread with its own event loop. That works for sync
host callers but breaks when a callback touches a request-scoped async
resource (asyncpg connection, aiosqlite session, etc.) because those are
bound to the request's event loop.

This module evaluates async callbacks on the request loop *before*
:meth:`InertiaResponse.to_asgi_response` runs, while DI scope is still
alive. After resolution, each prop's ``_evaluated``/``_result`` cache makes
its ``render()`` short-circuit at the top, so the portal path becomes
inert for user callbacks.
"""

import inspect
from collections.abc import Mapping
from typing import Any

from litestar_vite.inertia.helpers import (
    DeferredProp,
    OnceProp,
    OptionalProp,
    is_deferred_prop,
    is_once_prop,
    is_optional_prop,
    should_render,
)

__all__ = ("aresolve_props", "has_unresolved_async_callback")


def has_unresolved_async_callback(  # noqa: PLR0911
    value: Any,
    *,
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
    _key: "str | None" = None,
) -> bool:
    """Return ``True`` if ``value`` (recursively) contains a special prop
    that will be rendered for this request AND whose async callback hasn't
    been evaluated yet.

    Mirrors :func:`should_render` filtering so out-of-scope props (an
    ``optional()`` on a full page load, a ``defer()`` not in ``partial_data``)
    don't count — preserving the laziness contract and preventing
    infinite re-deferral when ``InertiaResponse.to_asgi_response`` re-enters
    after async resolution.
    """
    if not should_render(value, partial_data, partial_except, except_once_props, key=_key):
        return False
    if is_optional_prop(value):
        return not value._evaluated and inspect.iscoroutinefunction(value._callback)
    if is_deferred_prop(value):
        cb = value._value
        return not value._evaluated and cb is not None and inspect.iscoroutinefunction(cb)
    if is_once_prop(value):
        cb = value._value
        return not value._evaluated and callable(cb) and inspect.iscoroutinefunction(cb)
    if isinstance(value, str):
        return False
    if isinstance(value, Mapping):
        return any(
            has_unresolved_async_callback(
                v, partial_data=partial_data, partial_except=partial_except, except_once_props=except_once_props, _key=k
            )
            for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(
            has_unresolved_async_callback(
                v, partial_data=partial_data, partial_except=partial_except, except_once_props=except_once_props
            )
            for v in value
        )
    return False


async def aresolve_props(
    value: Any,
    *,
    partial_data: "set[str] | None" = None,
    partial_except: "set[str] | None" = None,
    except_once_props: "set[str] | None" = None,
) -> Any:
    """Walk ``value`` and ``await`` async prop callbacks on the current loop.

    Mirrors the filter logic of :func:`lazy_render` so we only evaluate props
    that will actually be rendered for this request — preserving the laziness
    contract of ``defer()``/``optional()`` on full page loads.

    Mutates :class:`DeferredProp`/:class:`OnceProp`/:class:`OptionalProp`
    instances in place by setting ``_evaluated=True`` and ``_result=<value>``.
    Sync callbacks and already-evaluated props are left untouched.

    Args:
        value: The response content (typically a ``dict``).
        partial_data: ``X-Inertia-Partial-Data`` keys, when present.
        partial_except: ``X-Inertia-Partial-Except`` keys (v2 protocol).
        except_once_props: Once-prop keys cached client-side.

    Returns:
        ``value`` (unchanged reference; mutations are in-place on prop objects).
    """
    if isinstance(value, Mapping):
        for k, v in value.items():
            if not should_render(v, partial_data, partial_except, except_once_props, key=k):
                continue
            await _aresolve_one(v, partial_data, partial_except, except_once_props)
        return value

    if isinstance(value, (list, tuple)):
        for v in value:
            if not should_render(v, partial_data, partial_except, except_once_props):
                continue
            await _aresolve_one(v, partial_data, partial_except, except_once_props)
        return value

    await _aresolve_one(value, partial_data, partial_except, except_once_props)
    return value


async def _aresolve_one(
    value: Any, partial_data: "set[str] | None", partial_except: "set[str] | None", except_once_props: "set[str] | None"
) -> None:
    if is_optional_prop(value):
        await _evaluate_optional(value)
        return
    if is_deferred_prop(value):
        await _evaluate_deferred(value)
        return
    if is_once_prop(value):
        await _evaluate_once(value)
        return
    if isinstance(value, (Mapping, list, tuple)):
        await aresolve_props(
            value, partial_data=partial_data, partial_except=partial_except, except_once_props=except_once_props
        )


async def _evaluate_optional(prop: "OptionalProp[Any, Any]") -> None:
    if prop._evaluated:
        return
    cb = prop._callback
    if inspect.iscoroutinefunction(cb):
        prop._result = await cb()
        prop._evaluated = True


async def _evaluate_deferred(prop: "DeferredProp[Any, Any]") -> None:
    if prop._evaluated:
        return
    cb = prop._value
    if cb is not None and callable(cb) and inspect.iscoroutinefunction(cb):
        prop._result = await cb()
        prop._evaluated = True


async def _evaluate_once(prop: "OnceProp[Any, Any]") -> None:
    if prop._evaluated:
        return
    cb = prop._value
    if callable(cb) and inspect.iscoroutinefunction(cb):
        prop._result = await cb()
        prop._evaluated = True
