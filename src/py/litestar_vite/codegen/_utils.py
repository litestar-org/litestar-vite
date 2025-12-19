"""Utilities for deterministic code generation and file output."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def deep_sort_dict(obj: Any) -> Any:
    """Recursively sort all dictionary keys for deterministic JSON output.

    Args:
        obj: Any Python object (dict, list, or primitive).

    Returns:
        The object with all nested dict keys sorted.
    """
    if isinstance(obj, dict):
        # pyright: ignore - intentionally working with Any types for generic dict sorting
        return {k: deep_sort_dict(v) for k, v in sorted(obj.items())}  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
    if isinstance(obj, list):
        return [deep_sort_dict(item) for item in obj]  # pyright: ignore[reportUnknownVariableType]
    return obj


def strip_timestamp_for_comparison(content: bytes) -> bytes:
    """Remove generatedAt and other timestamp fields for content comparison.

    This allows comparing file content while ignoring fields that change
    on every generation (like timestamps).

    Args:
        content: JSON content as bytes.

    Returns:
        JSON content with timestamp fields removed, sorted keys.
    """
    try:
        data = json.loads(content)
        # Remove fields that change on every generation
        data.pop("generatedAt", None)
        # Return sorted JSON for consistent comparison
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (json.JSONDecodeError, TypeError, AttributeError):
        # If we can't parse the content, return as-is
        return content


def write_if_changed(
    path: Path,
    content: bytes | str,
    *,
    normalize_for_comparison: Callable[[bytes], bytes] | None = None,
    encoding: str = "utf-8",
) -> bool:
    """Write content to file only if it differs from the existing content.

    Uses hash comparison to avoid unnecessary writes that would trigger
    file watchers and unnecessary rebuilds. Optionally normalizes content
    before comparison (e.g., to strip timestamps).

    Args:
        path: The file path to write to.
        content: The content to write (bytes or str).
        normalize_for_comparison: Optional callback to normalize content before
            comparison (e.g., strip timestamps). The file is written with the
            original content, not the normalized version.
        encoding: Encoding for string content.

    Returns:
        True if file was written (content changed), False if skipped (unchanged).
    """
    # Ensure trailing newline for POSIX compliance
    if isinstance(content, str):
        if not content.endswith("\n"):
            content += "\n"
        content_bytes = content.encode(encoding)
    else:
        if not content.endswith(b"\n"):
            content += b"\n"
        content_bytes = content

    if path.exists():
        try:
            existing = path.read_bytes()

            # Normalize both for comparison if a normalizer is provided
            if normalize_for_comparison:
                existing_normalized = normalize_for_comparison(existing)
                new_normalized = normalize_for_comparison(content_bytes)
            else:
                existing_normalized = existing
                new_normalized = content_bytes

            # Compare using MD5 hash for efficiency
            existing_hash = hashlib.md5(existing_normalized).hexdigest()  # noqa: S324
            new_hash = hashlib.md5(new_normalized).hexdigest()  # noqa: S324
            if existing_hash == new_hash:
                return False
        except OSError:
            pass

    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding=encoding)
    else:
        path.write_bytes(content)
    return True


def encode_deterministic_json(
    data: dict[str, Any], *, indent: int = 2, serializer: Callable[[Any], bytes] | None = None
) -> bytes:
    """Encode JSON with sorted keys for deterministic output.

    This is a wrapper that ensures all nested dict keys are sorted
    before serialization, producing byte-identical output for the
    same input data regardless of insertion order.

    Args:
        data: Dictionary to encode.
        indent: Indentation level for formatting.
        serializer: Optional custom serializer function. If not provided,
            uses litestar's default encode_json.

    Returns:
        Formatted JSON bytes with sorted keys.
    """
    import msgspec
    from litestar.serialization import encode_json

    sorted_data = deep_sort_dict(data)
    if serializer is not None:
        content = msgspec.json.format(serializer(sorted_data), indent=indent)
    else:
        content = msgspec.json.format(encode_json(sorted_data), indent=indent)
    # Ensure trailing newline for POSIX compliance
    if not content.endswith(b"\n"):
        content += b"\n"
    return content
