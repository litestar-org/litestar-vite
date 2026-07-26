from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection


_TRANSIENT_STATE_SCOPE_KEY = "_litestar_vite_inertia_shared"


def _empty_shared() -> "dict[str, Any]":
    return {}


def _empty_flash() -> "dict[str, list[str]]":
    return {}


def _empty_errors() -> "dict[str, str]":
    return {}


@dataclass
class InertiaTransientState:
    """Current-request state staged by Inertia helpers."""

    shared: dict[str, Any] = field(default_factory=_empty_shared)
    flash: dict[str, list[str]] = field(default_factory=_empty_flash)
    errors: dict[str, str] = field(default_factory=_empty_errors)
    clear_history: bool = False


@dataclass(frozen=True)
class RedirectStatePersistence:
    """Result of attempting to persist transient state across a redirect."""

    had_pending: bool
    persisted: bool
    dropped_keys: tuple[str, ...] = ()


def _scope(connection: "ASGIConnection[Any, Any, Any, Any]") -> "dict[str, Any]":
    scope = getattr(connection, "scope", None)
    if not isinstance(scope, dict):
        msg = "Inertia transient state requires a mutable ASGI scope."
        raise ImproperlyConfiguredException(msg)
    return cast("dict[str, Any]", scope)


def _coerce_transient_state(value: Any) -> "InertiaTransientState | None":
    if isinstance(value, InertiaTransientState):
        return value
    if isinstance(value, Mapping):
        return InertiaTransientState(shared=dict(cast("Mapping[str, Any]", value)))
    return None


def get_transient_state(connection: "ASGIConnection[Any, Any, Any, Any]") -> InertiaTransientState:
    """Return the connection's transient state, creating it when absent."""
    scope = _scope(connection)
    state = _coerce_transient_state(scope.get(_TRANSIENT_STATE_SCOPE_KEY))
    if state is None:
        state = InertiaTransientState()
    scope[_TRANSIENT_STATE_SCOPE_KEY] = state
    return state


def peek_transient_state(connection: "ASGIConnection[Any, Any, Any, Any]") -> "InertiaTransientState | None":
    """Return transient state without creating or consuming it."""
    scope = _scope(connection)
    value = scope.get(_TRANSIENT_STATE_SCOPE_KEY)
    state = _coerce_transient_state(value)
    if state is not None and state is not value:
        scope[_TRANSIENT_STATE_SCOPE_KEY] = state
    return state


def consume_transient_state(connection: "ASGIConnection[Any, Any, Any, Any]") -> InertiaTransientState:
    """Remove and return all transient state from the connection."""
    value = _scope(connection).pop(_TRANSIENT_STATE_SCOPE_KEY, None)
    return _coerce_transient_state(value) or InertiaTransientState()


def _discard_empty_state(connection: "ASGIConnection[Any, Any, Any, Any]", state: InertiaTransientState) -> None:
    if state.shared or state.flash or state.errors or state.clear_history:
        return
    scope = _scope(connection)
    if scope.get(_TRANSIENT_STATE_SCOPE_KEY) is state:
        scope.pop(_TRANSIENT_STATE_SCOPE_KEY, None)


def stage_shared(connection: "ASGIConnection[Any, Any, Any, Any]", key: str, value: Any) -> None:
    """Stage one raw shared prop for the current response."""
    get_transient_state(connection).shared[key] = value


def stage_flash(connection: "ASGIConnection[Any, Any, Any, Any]", message: str, category: str = "info") -> None:
    """Append one flash message for the current response."""
    get_transient_state(connection).flash.setdefault(category, []).append(message)


def stage_error(connection: "ASGIConnection[Any, Any, Any, Any]", key: str, message: str) -> None:
    """Stage one validation error for the current response."""
    get_transient_state(connection).errors[key] = message


def stage_clear_history(connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
    """Mark the current response as clearing encrypted browser history."""
    get_transient_state(connection).clear_history = True


def consume_shared(connection: "ASGIConnection[Any, Any, Any, Any]") -> "dict[str, Any]":
    """Consume current-request shared props."""
    state = peek_transient_state(connection)
    if state is None:
        return {}
    shared = state.shared
    state.shared = {}
    _discard_empty_state(connection, state)
    return shared


def consume_flash(connection: "ASGIConnection[Any, Any, Any, Any]") -> "dict[str, list[str]]":
    """Consume current-request flash messages."""
    state = peek_transient_state(connection)
    if state is None:
        return {}
    flash = state.flash
    state.flash = {}
    _discard_empty_state(connection, state)
    return flash


def consume_errors(connection: "ASGIConnection[Any, Any, Any, Any]") -> "dict[str, str]":
    """Consume current-request validation errors."""
    state = peek_transient_state(connection)
    if state is None:
        return {}
    errors = state.errors
    state.errors = {}
    _discard_empty_state(connection, state)
    return errors


def consume_clear_history(connection: "ASGIConnection[Any, Any, Any, Any]") -> bool:
    """Consume the current-request clear-history flag."""
    state = peek_transient_state(connection)
    if state is None:
        return False
    clear_history = state.clear_history
    state.clear_history = False
    _discard_empty_state(connection, state)
    return clear_history


def _session(connection: "ASGIConnection[Any, Any, Any, Any]") -> "dict[str, Any] | None":
    try:
        return connection.session
    except (AttributeError, ImproperlyConfiguredException):
        return None


def has_redirect_state_transport(connection: "ASGIConnection[Any, Any, Any, Any]") -> bool:
    """Return whether this request exposes a writable session transport."""
    return _session(connection) is not None


def persist_transient_state_for_redirect(connection: "ASGIConnection[Any, Any, Any, Any]") -> RedirectStatePersistence:
    """Persist supported transient state into the legacy session wire keys."""
    state = peek_transient_state(connection)
    had_pending = bool(state and (state.shared or state.flash or state.errors or state.clear_history))
    if not had_pending or state is None:
        return RedirectStatePersistence(had_pending=False, persisted=False)

    session = _session(connection)
    if session is None:
        return RedirectStatePersistence(had_pending=True, persisted=False)

    from litestar_vite.inertia.helpers import (
        _UNMATERIALIZABLE_SHARED,  # pyright: ignore[reportPrivateUsage]
        _materialize_shared_value,  # pyright: ignore[reportPrivateUsage]
    )

    dropped_keys: list[str] = []
    if state.shared:
        raw_session_shared: Any = session.setdefault("_shared", {})
        session_shared = cast("dict[str, Any]", raw_session_shared) if isinstance(raw_session_shared, dict) else {}
        if session_shared is not raw_session_shared:
            session["_shared"] = session_shared
        for key, value in state.shared.items():
            materialized = _materialize_shared_value(value)
            if materialized is _UNMATERIALIZABLE_SHARED:
                dropped_keys.append(key)
                continue
            session_shared[key] = materialized

    if state.flash:
        raw_messages: Any = session.setdefault("_messages", [])
        session_messages = cast("list[dict[str, str]]", raw_messages) if isinstance(raw_messages, list) else []
        if session_messages is not raw_messages:
            session["_messages"] = session_messages
        for category, messages in state.flash.items():
            session_messages.extend({"category": category, "message": message} for message in messages)

    if state.errors:
        raw_errors: Any = session.setdefault("_errors", {})
        session_errors = cast("dict[str, str]", raw_errors) if isinstance(raw_errors, dict) else {}
        if session_errors is not raw_errors:
            session["_errors"] = session_errors
        session_errors.update(state.errors)

    if state.clear_history:
        session["_inertia_clear_history"] = True

    consume_transient_state(connection)
    dropped = tuple(dropped_keys)
    return RedirectStatePersistence(had_pending=True, persisted=not dropped, dropped_keys=dropped)
