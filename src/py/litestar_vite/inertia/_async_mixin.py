"""Async rendering mixin for Inertia prop classes.

This module provides shared functionality for prop classes that need to
handle async callables via blocking portal execution.
"""

import inspect
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar

from anyio.from_thread import BlockingPortal, start_blocking_portal

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator

T = TypeVar("T")


class AsyncRenderMixin:
    """Mixin providing async rendering utilities for prop classes.

    This mixin provides two static methods used by DeferredProp, OnceProp,
    and OptionalProp to handle async callable resolution:

    - ``with_portal``: Context manager for obtaining a BlockingPortal
    - ``_is_awaitable``: Type guard for checking if a callable is async

    Example::

        class MyProp(AsyncRenderMixin, Generic[PropKeyT, T]):
            def render(self, portal: BlockingPortal | None = None) -> T | None:
                if self._is_awaitable(self._callback):
                    with self.with_portal(portal) as p:
                        return p.call(self._callback)
                return self._callback()
    """

    @staticmethod
    @contextmanager
    def with_portal(portal: "BlockingPortal | None" = None) -> "Generator[BlockingPortal, None, None]":
        """Get or create a blocking portal for async execution.

        Args:
            portal: Optional existing portal to reuse. If None, creates a new one.

        Yields:
            A BlockingPortal for executing async code from sync context.

        Example::

            with self.with_portal(portal) as p:
                result = p.call(async_function)
        """
        if portal is None:
            with start_blocking_portal() as p:
                yield p
        else:
            yield portal

    @staticmethod
    def _is_awaitable(v: "Callable[..., T | Coroutine[Any, Any, T]]") -> "TypeGuard[Coroutine[Any, Any, T]]":
        """Check if a callable is an async coroutine function.

        Args:
            v: The callable to check.

        Returns:
            True if the callable is an async coroutine function.
        """
        return inspect.iscoroutinefunction(v)
