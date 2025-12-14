"""SPA mode handler public API.

The SPA handler implementation lives in ``litestar_vite._handler.app``. This module exists as a stable import
location for users and tests.
"""

from litestar_vite._handler.app import AppHandler

__all__ = ("AppHandler",)
