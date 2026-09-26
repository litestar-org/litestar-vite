"""AsyncAPI plugin discovery and document normalization for Litestar."""

import contextlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote

import msgspec

from litestar_vite.typing import ASYNCAPI_INSTALLED

if TYPE_CHECKING:
    from litestar import Litestar

ASYNCAPI_DOCS_DEFAULT_PATH = "/asyncapi"
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")


def _slug_segment(segment: str) -> str:
    """Sanitize a path segment for use in an AsyncAPI channel key.

    Path parameter segments shaped {name} or {name:converter} return 'p_' followed
    by the sanitized parameter name. Any other segment has every run of characters
    outside [A-Za-z0-9] replaced by a single underscore.

    Args:
        segment: Path segment string.

    Returns:
        Sanitized segment string.
    """
    if segment.startswith("{") and segment.endswith("}"):
        inner = segment[1:-1]
        name = inner.split(":", 1)[0]
        sanitized = _NON_ALNUM_RE.sub("_", name)
        return f"p_{sanitized}"
    return _NON_ALNUM_RE.sub("_", segment)


def _channel_key_base(normalized_address: str) -> str:
    """Build a deterministic base channel key from a route address.

    Strips the leading slash, splits on slash, drops empty segments, applies
    _slug_segment to each, and joins with double underscores. An empty result
    returns 'root'.

    Args:
        normalized_address: The normalized route path.

    Returns:
        Deterministic base channel key.
    """
    segments = [_slug_segment(s) for s in normalized_address.lstrip("/").split("/") if s]
    return "__".join(segments) or "root"


@dataclass(slots=True)
class _ChannelKeyAllocator:
    """Allocate collision-safe channel keys across realtime sources."""

    assigned: dict[tuple[str, str], str] = field(default_factory=dict[tuple[str, str], str])
    taken: set[str] = field(default_factory=set[str])

    def allocate(self, normalized_address: str, source: str) -> str:
        """Allocate a unique channel key for a given route address and source.

        Two different sources at the same address deliberately receive different
        channel keys to prevent collisions and ensure intact operations.

        Args:
            normalized_address: The normalized route address string.
            source: Realtime source identifier ('websocket', 'channels', or 'sse').

        Returns:
            Collision-safe unique channel key.
        """
        pair = (normalized_address, source)
        if pair in self.assigned:
            return self.assigned[pair]

        base = _channel_key_base(normalized_address)
        candidate = base
        counter = 2
        while candidate in self.taken:
            candidate = f"{base}_{counter}"
            counter += 1

        self.taken.add(candidate)
        self.assigned[pair] = candidate
        return candidate


def _unescape_json_pointer(segment: str) -> str:
    """Unescape an RFC 6901 URI-fragment JSON Pointer token.

    Args:
        segment: Escaped JSON Pointer token.

    Returns:
        Unescaped string token.
    """
    return unquote(segment).replace("~1", "/").replace("~0", "~")


def find_asyncapi_plugin(app: "Litestar") -> Any | None:
    """Find an AsyncAPI plugin registered on the Litestar application.

    Queries Litestar's plugin registry for a registered ``AsyncAPIPlugin``,
    guarded by ``ASYNCAPI_INSTALLED``.

    Args:
        app: The Litestar application instance.

    Returns:
        The registered AsyncAPI plugin instance if found, otherwise None.
    """
    if not ASYNCAPI_INSTALLED:
        return None

    plugins = getattr(app, "plugins", None)
    if plugins is not None and hasattr(plugins, "get"):
        with contextlib.suppress(KeyError, AttributeError):
            from litestar_asyncapi import AsyncAPIPlugin

            return plugins.get(AsyncAPIPlugin)
        with contextlib.suppress(KeyError, AttributeError):
            return plugins.get("AsyncAPIPlugin")
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


def _matches_channel_ref(ch_ref: Any, old_key: str) -> bool:
    """Return True if a channel $ref points to old_key (raw or RFC 6901 escaped).

    Args:
        ch_ref: The $ref string from an operation channel object.
        old_key: The original channel key in the document.

    Returns:
        True when the reference targets old_key.
    """
    if not isinstance(ch_ref, str) or not ch_ref.startswith("#/channels/"):
        return False
    raw_ref_key = ch_ref.removeprefix("#/channels/")
    return raw_ref_key == old_key or _unescape_json_pointer(raw_ref_key) == old_key


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

        ops_for_channel: list[dict[str, Any]] = []
        for raw_op in raw_operations.values():
            if isinstance(raw_op, dict):
                typed_op = cast("dict[str, Any]", raw_op)
                ch_target = typed_op.get("channel")
                if isinstance(ch_target, dict) and _matches_channel_ref(
                    cast("dict[str, Any]", ch_target).get("$ref"), old_key
                ):
                    ops_for_channel.append(typed_op)

        if ch.get("bindings") is None:
            ch["bindings"] = _derive_channel_bindings(ch, ops_for_channel)

        if isinstance(ch.get("messages"), dict):
            normalized_messages: dict[str, Any] = {}
            for msg_key, raw_msg in cast("dict[str, Any]", ch["messages"]).items():
                if isinstance(raw_msg, dict):
                    msg_copy = cast("dict[str, Any]", raw_msg).copy()
                    msg_copy.setdefault("payload", {})
                    normalized_messages[msg_key] = msg_copy
                else:
                    normalized_messages[msg_key] = raw_msg
            ch["messages"] = normalized_messages

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


def _resolve_mapped_channel_key(raw_ref_key: str, old_to_new_keys: dict[str, str]) -> str | None:
    """Resolve a raw or RFC 6901 escaped channel key against old_to_new_keys.

    Args:
        raw_ref_key: Channel key segment from a $ref string.
        old_to_new_keys: Mapping of original channel keys to normalized keys.

    Returns:
        Normalized channel key if matched, otherwise None.
    """
    if raw_ref_key in old_to_new_keys:
        return old_to_new_keys[raw_ref_key]
    unescaped = _unescape_json_pointer(raw_ref_key)
    return old_to_new_keys.get(unescaped)


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
                mapped_ch_key = _resolve_mapped_channel_key(old_ref_key, old_to_new_keys)
                if mapped_ch_key is not None:
                    ch_ref_dict["$ref"] = f"#/channels/{mapped_ch_key}"
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
                        parts = remainder.rsplit("/messages/", 1)
                        ref_channel_key = parts[0]
                        mapped_key = _resolve_mapped_channel_key(ref_channel_key, old_to_new_keys)
                        if mapped_key is not None:
                            if len(parts) > 1:
                                msg_key = _unescape_json_pointer(parts[1])
                                msg_dict["$ref"] = f"#/channels/{mapped_key}/messages/{msg_key}"
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
) -> dict[str, Any] | None:
    """Resolve and normalize the AsyncAPI document from a registered AsyncAPIPlugin.

    Queries the Litestar application for a registered ``AsyncAPIPlugin`` via
    ``find_asyncapi_plugin``. When present, retrieves the schema from the plugin
    via ``get_asyncapi_schema`` (or ``get_asyncapi_json`` if a non-dict is returned)
    and normalizes channel keys and operation references for frontend code generation.
    When no ``AsyncAPIPlugin`` is registered, returns ``None``.

    Args:
        app: The Litestar application instance.
        title: Optional title override for the AsyncAPI document.
        version: Optional version override for the AsyncAPI document.

    Returns:
        Normalized AsyncAPI document dictionary when ``AsyncAPIPlugin`` is registered,
        otherwise ``None``.
    """
    plugin = find_asyncapi_plugin(app)
    if plugin is None:
        return None

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
            return normalized
    except (AttributeError, TypeError, ValueError):
        return None

    return None
