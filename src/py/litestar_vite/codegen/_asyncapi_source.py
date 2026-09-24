"""Progressive litestar-asyncapi integration and document normalization.

This module treats litestar-asyncapi as an optional progressive enhancement:
when it is installed and an AsyncAPI plugin is registered on the Litestar application,
its schema is preferred as the authoritative document source. When absent, failing,
or returning malformed data, the built-in introspection generator provides a working
zero-dependency fallback.

Documents from either source are normalized into a unified internal representation
using deterministic channel key allocation and protocol bindings, ensuring frontend
type generation produces identical TypeScript contracts regardless of the schema origin.
Reserved AsyncAPI documentation paths are also extracted to protect documentation endpoints
from the Vite dev-server Single Page Application (SPA) catch-all handler.
"""

from typing import TYPE_CHECKING, Any, cast

import msgspec

from litestar_vite.codegen._asyncapi import (
    _ChannelKeyAllocator,  # pyright: ignore[reportPrivateUsage]
    create_asyncapi_document,
)

if TYPE_CHECKING:
    from litestar import Litestar

ASYNCAPI_DOCS_DEFAULT_PATH = "/asyncapi"


def find_asyncapi_plugin(app: "Litestar") -> Any | None:
    """Find an AsyncAPI plugin registered on the Litestar application.

    Detection is duck-typed per asyncapi-schema-export REQ-EXPORT-3: any plugin
    exposing a get_asyncapi_schema attribute is treated as an AsyncAPI schema
    provider. This avoids importing litestar_asyncapi in the common execution path
    and keeps litestar-vite warning-free and error-free when the package is not installed.

    Args:
        app: The Litestar application instance.

    Returns:
        The registered AsyncAPI plugin instance if found, otherwise None.
    """
    for plugin in getattr(app, "plugins", ()):
        if hasattr(plugin, "get_asyncapi_schema"):
            return plugin
    return None


def asyncapi_docs_paths(app: "Litestar") -> tuple[str, ...]:
    """Return reserved AsyncAPI documentation route prefixes.

    When an AsyncAPI plugin is registered, returns a deduplicated tuple containing
    the default AsyncAPI documentation path ('/asyncapi') and any custom documentation
    path configured on the plugin. When no plugin is registered, returns an empty tuple.

    Args:
        app: The Litestar application instance.

    Returns:
        Tuple of reserved documentation path strings.
    """
    plugin = find_asyncapi_plugin(app)
    if plugin is None:
        return ()

    paths: list[str] = [ASYNCAPI_DOCS_DEFAULT_PATH]
    configured_path = getattr(getattr(getattr(plugin, "config", None), "docs", None), "path", None)
    if isinstance(configured_path, str) and configured_path.strip():
        paths.append(configured_path.strip())

    seen: set[str] = set()
    deduped: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            deduped.append(path)
    return tuple(deduped)


def _derive_channel_bindings(ch: dict[str, Any], ops_for_channel: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive default protocol bindings for a channel when omitted.

    When bindings are absent on the channel, derives WebSocket bindings if any operation
    has an action of 'receive' or the address starts with a WebSocket prefix. Derives HTTP
    SSE bindings if all operations are 'send' and any message specifies a 'text/event-stream'
    content type. Returns an empty bindings dict otherwise.

    Args:
        ch: The channel definition dictionary.
        ops_for_channel: Operations associated with this channel.

    Returns:
        A bindings dictionary containing protocol markers.
    """
    address_raw = ch.get("address")
    address_str = str(address_raw) if address_raw is not None else ""
    has_receive_op = any(op.get("action") == "receive" for op in ops_for_channel)
    is_ws_address = address_str.startswith(("ws://", "wss://", "/ws"))

    has_send_only = bool(ops_for_channel) and all(op.get("action") == "send" for op in ops_for_channel)
    channel_messages: dict[str, Any] = (
        cast("dict[str, Any]", ch.get("messages")) if isinstance(ch.get("messages"), dict) else {}
    )
    has_sse_content_type = (
        ch.get("defaultContentType") == "text/event-stream"
        or any(
            isinstance(m, dict) and cast("dict[str, Any]", m).get("contentType") == "text/event-stream"
            for m in channel_messages.values()
        )
        or any(
            isinstance(m, dict) and cast("dict[str, Any]", m).get("contentType") == "text/event-stream"
            for op in ops_for_channel
            for m in (cast("list[Any]", op.get("messages")) if isinstance(op.get("messages"), list) else [])
        )
    )

    if has_receive_op or is_ws_address:
        return {"ws": {}}
    if has_send_only and has_sse_content_type:
        return {"http": {}}
    return {}


def _prepare_channels(
    raw_channels: dict[str, Any], raw_operations: dict[str, Any], allocator: _ChannelKeyAllocator
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Normalize and re-key channels with collision-safe names.

    Iterates each raw channel, associates matching operations, derives protocol bindings
    if absent, and allocates a deterministic channel key using _ChannelKeyAllocator.

    Args:
        raw_channels: Dictionary of raw channels from the source document.
        raw_operations: Dictionary of operations from the source document.
        allocator: Channel key allocator instance.

    Returns:
        A tuple of (prepared_channels_map, old_to_new_keys_map).
    """
    old_to_new_keys: dict[str, str] = {}
    prepared_channels: dict[str, dict[str, Any]] = {}

    for old_key, channel_data in raw_channels.items():
        ch: dict[str, Any] = cast("dict[str, Any]", channel_data).copy() if isinstance(channel_data, dict) else {}
        target_channel_ref = f"#/channels/{old_key}"

        ops_for_channel: list[dict[str, Any]] = []
        for raw_op in raw_operations.values():
            if isinstance(raw_op, dict):
                typed_op = cast("dict[str, Any]", raw_op)
                ch_target = typed_op.get("channel")
                if isinstance(ch_target, dict) and cast("dict[str, Any]", ch_target).get("$ref") == target_channel_ref:
                    ops_for_channel.append(typed_op)

        if ch.get("bindings") is None:
            ch["bindings"] = _derive_channel_bindings(ch, ops_for_channel)

        bindings_dict: dict[str, Any] = (
            cast("dict[str, Any]", ch.get("bindings")) if isinstance(ch.get("bindings"), dict) else {}
        )
        if "ws" in bindings_dict:
            source = "websocket"
        elif "http" in bindings_dict:
            source = "sse"
        else:
            source = "channels"

        raw_address = ch.get("address")
        alloc_address = str(raw_address) if isinstance(raw_address, str) and raw_address else old_key
        new_key = allocator.allocate(alloc_address, source)
        old_to_new_keys[old_key] = new_key
        prepared_channels[new_key] = ch

    return prepared_channels, old_to_new_keys


def _rewrite_operation_references(raw_operations: dict[str, Any], old_to_new_keys: dict[str, str]) -> dict[str, Any]:
    """Rewrite operation channel and message references to target normalized keys.

    Updates channel $ref and message $ref paths in each operation to use newly
    allocated channel keys.

    Args:
        raw_operations: Dictionary of raw operations.
        old_to_new_keys: Mapping of old channel keys to normalized channel keys.

    Returns:
        Dictionary of updated operations.
    """
    new_operations: dict[str, Any] = {}
    for op_id, raw_op in raw_operations.items():
        if not isinstance(raw_op, dict):
            new_operations[op_id] = raw_op
            continue

        op: dict[str, Any] = cast("dict[str, Any]", raw_op).copy()
        ch_ref_raw = op.get("channel")
        if isinstance(ch_ref_raw, dict):
            ch_ref_dict = cast("dict[str, Any]", ch_ref_raw).copy()
            ch_ref = ch_ref_dict.get("$ref")
            if isinstance(ch_ref, str) and ch_ref.startswith("#/channels/"):
                old_ref_key = ch_ref.removeprefix("#/channels/")
                if old_ref_key in old_to_new_keys:
                    ch_ref_dict["$ref"] = f"#/channels/{old_to_new_keys[old_ref_key]}"
            op["channel"] = ch_ref_dict

        raw_messages = op.get("messages")
        if isinstance(raw_messages, list):
            new_messages: list[Any] = []
            for item in cast("list[Any]", raw_messages):
                if isinstance(item, dict):
                    msg_dict = cast("dict[str, Any]", item).copy()
                    msg_ref = msg_dict.get("$ref")
                    if isinstance(msg_ref, str) and msg_ref.startswith("#/channels/"):
                        remainder = msg_ref.removeprefix("#/channels/")
                        parts = remainder.split("/messages/", 1)
                        ref_channel_key = parts[0]
                        if ref_channel_key in old_to_new_keys:
                            mapped_key = old_to_new_keys[ref_channel_key]
                            if len(parts) > 1:
                                msg_dict["$ref"] = f"#/channels/{mapped_key}/messages/{parts[1]}"
                            else:
                                msg_dict["$ref"] = f"#/channels/{mapped_key}"
                    new_messages.append(msg_dict)
                else:
                    new_messages.append(item)
            op["messages"] = new_messages

        new_operations[op_id] = op

    return new_operations


def normalize_asyncapi_document(document: dict[str, Any]) -> dict[str, Any]:
    """Normalize an AsyncAPI document into a consistent internal shape.

    Guarantees that:

    1. The asyncapi version string is present ('3.0.0' or '3.1.0').
    2. Channels are re-keyed into collision-safe litestar-vite format using
       _ChannelKeyAllocator with protocol-aware source selection.
    3. Every channel has an explicit bindings dictionary with protocol markers.
    4. Operation channel and message $ref pointers match the allocated channel keys.
    5. Root document metadata, servers, and components are preserved intact.

    Args:
        document: Raw AsyncAPI document dictionary.

    Returns:
        A normalized AsyncAPI document dictionary.
    """
    normalized: dict[str, Any] = dict(document)
    raw_version = document.get("asyncapi")
    normalized["asyncapi"] = str(raw_version) if raw_version else "3.0.0"

    raw_channels: dict[str, Any] = (
        cast("dict[str, Any]", document.get("channels")) if isinstance(document.get("channels"), dict) else {}
    )
    raw_operations: dict[str, Any] = (
        cast("dict[str, Any]", document.get("operations")) if isinstance(document.get("operations"), dict) else {}
    )

    allocator = _ChannelKeyAllocator()
    prepared_channels, old_to_new_keys = _prepare_channels(raw_channels, raw_operations, allocator)
    normalized["channels"] = prepared_channels
    normalized["operations"] = _rewrite_operation_references(raw_operations, old_to_new_keys)
    return normalized


def resolve_asyncapi_document(
    app: "Litestar", title: str | None = None, version: str | None = None
) -> tuple[dict[str, Any], str]:
    """Resolve and normalize the AsyncAPI document for a Litestar application.

    Probes for a registered AsyncAPI plugin via find_asyncapi_plugin. When found,
    attempts to retrieve the schema from the plugin via get_asyncapi_schema (or
    get_asyncapi_json if a non-dict is returned). On any exception or malformed return,
    or when no plugin is present, falls back seamlessly to create_asyncapi_document.

    Both sources are passed through normalize_asyncapi_document to ensure identical
    internal channel keying and binding semantics for frontend code generation.

    Args:
        app: The Litestar application instance.
        title: Optional title override for the AsyncAPI document.
        version: Optional version override for the AsyncAPI document.

    Returns:
        Tuple of (normalized_document_dict, source_name) where source_name is
        either 'litestar-asyncapi' or 'builtin'.
    """
    builtin_kwargs: dict[str, Any] = {}
    if title is not None:
        builtin_kwargs["title"] = title
    if version is not None:
        builtin_kwargs["version"] = version

    plugin = find_asyncapi_plugin(app)
    if plugin is not None:
        try:
            raw_schema: Any = plugin.get_asyncapi_schema(app)
            schema: dict[str, Any] | None = None
            if isinstance(raw_schema, dict):
                schema = cast("dict[str, Any]", raw_schema)
            elif hasattr(plugin, "get_asyncapi_json"):
                raw_json: Any = plugin.get_asyncapi_json(app)
                decoded: Any = msgspec.json.decode(raw_json)
                if isinstance(decoded, dict):
                    schema = cast("dict[str, Any]", decoded)
            if schema is not None:
                normalized = normalize_asyncapi_document(schema)
                if title or version:
                    info = normalized.setdefault("info", {})
                    if title:
                        info["title"] = title
                    if version:
                        info["version"] = version
                return normalized, "litestar-asyncapi"
        except (AttributeError, TypeError, ValueError):
            pass

    builtin_doc = create_asyncapi_document(app, **builtin_kwargs).to_dict()
    return normalize_asyncapi_document(builtin_doc), "builtin"
