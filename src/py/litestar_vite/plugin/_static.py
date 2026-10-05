"""Server-neutral static-serving contract.

Describes where a Litestar Vite app's production static assets should be served
from: either directly by the web server (``NATIVE``) or by Litestar's static
router over ASGI (``ASGI``). The result is a plain dataclass with an explicit
``placement`` discriminator so an external consumer such as litestar-granian can
compare structurally (``config.placement == "native"``) without importing this
package. This module deliberately carries no litestar-granian import.
"""

import inspect
import re
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast

from litestar.exceptions import NotFoundException

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from litestar.connection import Request
    from litestar.datastructures import CacheControlHeader
    from litestar.openapi.spec import SecurityRequirement
    from litestar.response import Response
    from litestar.types import (
        AfterRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        AfterResponseHookHandler,  # pyright: ignore[reportUnknownVariableType]
        BeforeRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        ExceptionHandlersMap,
        Guard,  # pyright: ignore[reportUnknownVariableType]
        Middleware,
    )

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
BLOCKED_STATIC_METADATA_FILES: frozenset[str] = frozenset({
    "manifest.json",
    ".vite/manifest.json",
    "ssr-manifest.json",
    ".vite/ssr-manifest.json",
    ".litestar.json",
    "hot",
})
HASHED_ASSETS_DIR = "assets"
"""Directory name (Vite ``build.assetsDir`` default) that must be an ancestor of a hashed asset."""

_HASHED_ASSET_PATTERN = re.compile(r"[-.][A-Za-z0-9_-]{8,16}\.[A-Za-z0-9]+(?:\.map)?$")


def is_hashed_asset_path(file_path: "str | Path", assets_dir: str = HASHED_ASSETS_DIR) -> bool:
    """Return True when ``file_path`` is a Vite/Rollup content-hashed build artifact.

    Two conditions must hold so that hand-named files such as
    ``icon-192x192.png`` or ``vendor.ReactDOM.js`` outside the build output are
    never served as immutable:

    1. ``assets_dir`` is an ancestor directory of the file.
    2. The file name ends in a ``-<hash>.<ext>`` (optionally ``.map``) segment
       where ``<hash>`` is an 8-16 character base64url/hex digest, matching
       Rollup's default ``[name]-[hash][extname]`` templates.
    """
    path = Path(file_path)
    parts = path.as_posix().split("/")
    if assets_dir not in parts[:-1]:
        return False
    return bool(_HASHED_ASSET_PATTERN.search(path.name))


def is_blocked_static_metadata_path(relative_path: str, extra_blocked: "Iterable[str]" = ()) -> bool:
    """Return True when ``relative_path`` targets an internal build or bridge metadata file."""
    normalized = relative_path.replace("\\", "/").strip("/").lower()
    if not normalized:
        return False
    blocked = BLOCKED_STATIC_METADATA_FILES.union(
        item.replace("\\", "/").strip("/").lower() for item in extra_blocked if item
    )
    if normalized in blocked:
        return True
    parts = normalized.split("/")
    return ".litestar.json" in parts or normalized.endswith(("/.vite/manifest.json", "/.vite/ssr-manifest.json"))


class _StaticBeforeRequestHook:
    """Callable before_request hook that blocks internal metadata files before delegating to user hook."""

    __slots__ = ("_asset_prefix", "_blocked_paths", "_user_hook")

    def __init__(self, *, asset_url: str, blocked_paths: frozenset[str], user_hook: Any = None) -> None:
        self._asset_prefix = "/" + asset_url.strip("/") if asset_url.strip("/") else ""
        self._blocked_paths = blocked_paths
        self._user_hook = user_hook

    async def __call__(self, request: "Request[Any, Any, Any]") -> Any:
        file_param = request.path_params.get("file_path")
        if file_param is not None:
            rel_path = str(file_param).replace("\\", "/").strip("/")
        else:
            req_path = request.url.path
            if self._asset_prefix and req_path.startswith(f"{self._asset_prefix}/"):
                rel_path = req_path[len(self._asset_prefix) + 1 :].strip("/")
            else:
                rel_path = req_path.strip("/")

        if is_blocked_static_metadata_path(rel_path, self._blocked_paths):
            raise NotFoundException(detail="Static metadata file not found")

        if self._user_hook is not None:
            result = self._user_hook(request)
            if inspect.isawaitable(result):
                return await result
            return result
        return None


class _StaticAfterRequestHook:
    """Callable after_request hook that sets immutable Cache-Control on hashed assets."""

    __slots__ = ("_immutable_cache_headers", "_user_hook")

    def __init__(self, *, immutable_cache_headers: bool, user_hook: Any = None) -> None:
        self._immutable_cache_headers = immutable_cache_headers
        self._user_hook = user_hook

    async def __call__(self, response: "Response[Any]") -> "Response[Any]":
        if self._immutable_cache_headers:
            file_path = getattr(response, "file_path", None)
            if file_path is not None and is_hashed_asset_path(file_path):
                headers = getattr(response, "headers", None)
                if headers is not None and "cache-control" not in headers and "Cache-Control" not in headers:
                    headers["cache-control"] = IMMUTABLE_CACHE_CONTROL

        if self._user_hook is not None:
            result = self._user_hook(response)
            if inspect.isawaitable(result):
                return cast("Response[Any]", await result)
            return cast("Response[Any]", result)
        return response


def build_static_before_request_hook(
    *, asset_url: str, manifest_name: str = "manifest.json", hot_file: str = "hot", user_hook: Any = None
) -> "_StaticBeforeRequestHook":
    """Build a static router before_request hook that blocks internal Vite metadata files."""
    clean_manifest = manifest_name.replace("\\", "/").strip("/")
    clean_hot = hot_file.replace("\\", "/").strip("/")
    blocked = BLOCKED_STATIC_METADATA_FILES.union({clean_manifest, f".vite/{clean_manifest}", clean_hot})
    return _StaticBeforeRequestHook(asset_url=asset_url, blocked_paths=blocked, user_hook=user_hook)


def build_static_after_request_hook(
    *, immutable_cache_headers: bool, user_hook: Any = None
) -> "_StaticAfterRequestHook":
    """Build a static router after_request hook that attaches immutable Cache-Control to hashed assets."""
    return _StaticAfterRequestHook(immutable_cache_headers=immutable_cache_headers, user_hook=user_hook)


class StaticPlacement(str, Enum):
    """Where static files are served from.

    Subclassing ``str`` is deliberate: consumers compare structurally against the
    literal value (``config.placement == "native"``) without importing this package.
    """

    NATIVE = "native"
    ASGI = "asgi"


@dataclass(frozen=True, slots=True)
class StaticServerMount:
    """Describe one static directory exposed to a native server."""

    route: str
    directory: Path
    directory_index: str | None = None


@dataclass(frozen=True, slots=True)
class StaticServerConfig:
    """Describe where static files should be served from.

    ``reason`` is diagnostic detail that is meaningful only when ``placement`` is
    ``ASGI``; it explains why Litestar's static router must serve (development mode,
    framework/SSR routing, manifest/build-state problems, and similar).
    """

    placement: StaticPlacement = StaticPlacement.ASGI
    mounts: tuple[StaticServerMount, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        """Enforce the placement invariants.

        Raises:
            ValueError: If ``NATIVE`` has no mounts, ``NATIVE`` carries a reason, or
                ``ASGI`` lacks a non-empty reason.
        """
        if self.placement is StaticPlacement.NATIVE:
            if not self.mounts:
                msg = "StaticServerConfig with NATIVE placement requires at least one mount."
                raise ValueError(msg)
            if self.reason is not None:
                msg = "StaticServerConfig with NATIVE placement must not carry a reason; reason is ASGI-only detail."
                raise ValueError(msg)
        elif not self.reason:
            msg = "StaticServerConfig with ASGI placement requires a non-empty reason."
            raise ValueError(msg)


@dataclass
class StaticFilesConfig:
    """Configuration for static file serving.

    Field names must match keyword parameters of Litestar's ``create_static_files_router``;
    :meth:`as_router_kwargs` forwards the set fields to it.
    """

    after_request: "AfterRequestHookHandler | None" = None
    after_response: "AfterResponseHookHandler | None" = None
    before_request: "BeforeRequestHookHandler | None" = None
    cache_control: "CacheControlHeader | None" = None
    exception_handlers: "ExceptionHandlersMap | None" = None
    guards: "list[Guard] | None" = None  # pyright: ignore[reportUnknownVariableType]
    middleware: "Sequence[Middleware] | None" = None
    opt: "dict[str, Any] | None" = None
    security: "Sequence[SecurityRequirement] | None" = None
    tags: "Sequence[str] | None" = None

    _NOT_ROUTER_KWARGS: "ClassVar[frozenset[str]]" = frozenset({"opt"})
    _METADATA_FIELDS: "ClassVar[frozenset[str]]" = frozenset({"opt", "security", "tags"})

    def as_router_kwargs(self) -> "dict[str, Any]":
        """Return the explicitly-set fields as ``create_static_files_router`` keyword arguments.

        ``opt`` is excluded because the plugin merges it with its own options. Unset fields
        are omitted so Litestar's defaults apply.

        Returns:
            Keyword arguments for ``create_static_files_router``.
        """
        kwargs: "dict[str, Any]" = {}
        for field_info in fields(self):
            if field_info.name in self._NOT_ROUTER_KWARGS:
                continue
            value: "Any" = getattr(self, field_info.name)
            if value is not None:
                kwargs[field_info.name] = value
        return kwargs

    def asgi_override_fields(self) -> list[str]:
        """Return the list of configured fields that require ASGI request/response serving.

        Empty containers count as unset: they configure no runtime behavior.

        Returns:
            Names of set non-metadata fields that modify runtime ASGI behavior.
        """
        return [
            field_info.name
            for field_info in fields(self)
            if field_info.name not in self._METADATA_FIELDS and getattr(self, field_info.name)
        ]

    def has_asgi_overrides(self) -> bool:
        """Return True if any configured field alters runtime ASGI request/response behavior.

        Returns:
            True if any ASGI-dependent field is set, False if the configuration is pure metadata.
        """
        return bool(self.asgi_override_fields())
