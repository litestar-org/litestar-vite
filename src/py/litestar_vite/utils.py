"""Utility helpers for litestar-vite."""

from __future__ import annotations

import os
from importlib.util import find_spec
from pathlib import Path
from typing import Any


def get_package_path(*parts: str) -> Path:
    """Resolve a path inside the installed litestar-vite package.

    Args:
        *parts: Path segments relative to the package root.

    Returns:
        The resolved package path.
    """
    spec = find_spec("litestar_vite")
    if spec and spec.origin:
        return Path(spec.origin).parent.joinpath(*parts)
    # Fallback for uncommon import contexts.
    return Path(__file__).resolve().parent.joinpath(*parts)


def get_static_resource_path(filename: str) -> Path:
    """Resolve a bundled static resource path.

    Args:
        filename: Static file name inside the package static directory.

    Returns:
        Path to the bundled resource.
    """
    return get_package_path("static", filename)


def read_text_file(path: Path, *, encoding: str = "utf-8") -> str:
    """Read a text file with consistent encoding.

    Args:
        path: File path to read.
        encoding: Text encoding.

    Returns:
        File contents.
    """
    return path.read_text(encoding=encoding)


def read_hotfile_url(hotfile_path: Path) -> str:
    """Read and normalize the Vite hotfile URL.

    Returns:
        The Vite server URL from the hotfile, stripped of surrounding whitespace.
    """
    return read_text_file(hotfile_path).strip()


# Per-process cache for ``read_bridge_config``: ``{resolved_path: (mtime_ns, parsed_dict)}``.
# Strategy: mtime-based revalidation per call (Decision Point 1 option (a)).
# The ``Path.stat()`` cost is sub-microsecond; in exchange we kill the entire class of
# "stale cache after dev restart" bugs and avoid forcing tests to call ``cache_clear``.
_BRIDGE_CACHE: dict[str, tuple[int, dict[str, Any]]] = {}


def _resolve_bridge_path(path: Path | None) -> Path:
    """Resolve which ``.litestar.json`` to read.

    Resolution order:
        1. Explicit ``path`` argument when provided.
        2. ``LITESTAR_VITE_CONFIG_PATH`` env var when set.
        3. ``<cwd>/.litestar.json``.
    """
    if path is not None:
        return path
    env_path = os.environ.get("LITESTAR_VITE_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    return Path.cwd() / ".litestar.json"


def read_bridge_config(path: Path | None = None) -> dict[str, Any] | None:
    """Read the Litestar/Vite bridge config (``.litestar.json``).

    Resolution order for ``path``:
        1. Explicit ``path`` argument when provided.
        2. ``LITESTAR_VITE_CONFIG_PATH`` env var when set.
        3. ``<cwd>/.litestar.json``.

    Returns:
        The parsed JSON object as a dict, or ``None`` if the file is missing,
        unreadable, or does not parse as a JSON object.

    Caching:
        Per-process result cache keyed by resolved path; invalidated on mtime
        change (a single ``Path.stat()`` per call). Use
        ``read_bridge_config.cache_clear()`` in tests when the cache must be
        flushed independently of mtime (e.g., when forcing the same path to be
        re-parsed without advancing its mtime).
    """
    resolved = _resolve_bridge_path(path)
    key = str(resolved)
    try:
        stat = resolved.stat()
    except (FileNotFoundError, OSError):
        _BRIDGE_CACHE.pop(key, None)
        return None

    mtime_ns = stat.st_mtime_ns
    cached = _BRIDGE_CACHE.get(key)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]

    try:
        raw = resolved.read_bytes()
    except (FileNotFoundError, OSError):
        _BRIDGE_CACHE.pop(key, None)
        return None

    # Defer the msgspec import: ``utils`` is imported during plugin init and we
    # do not want a hard requirement on a heavy dependency for unrelated callers.
    import msgspec

    try:
        parsed = msgspec.json.decode(raw)
    except msgspec.DecodeError:
        _BRIDGE_CACHE.pop(key, None)
        return None
    if not isinstance(parsed, dict):
        _BRIDGE_CACHE.pop(key, None)
        return None

    _BRIDGE_CACHE[key] = (mtime_ns, parsed)
    return parsed


def _cache_clear() -> None:
    """Drop the per-process bridge-config cache (test helper)."""
    _BRIDGE_CACHE.clear()


# Mirror ``functools.lru_cache``'s ``cache_clear`` attribute for ergonomic test use.
read_bridge_config.cache_clear = _cache_clear  # type: ignore[attr-defined]
