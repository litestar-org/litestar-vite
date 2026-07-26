import logging
from types import MappingProxyType
from typing import Any
from unittest.mock import MagicMock

import pytest
from litestar.types import Empty

from litestar_vite.inertia.helpers import defer
from litestar_vite.inertia.state import (
    RedirectStatePersistence,
    has_redirect_state_transport,
    peek_transient_state,
    persist_transient_state_for_redirect,
    stage_clear_history,
    stage_error,
    stage_flash,
    stage_shared,
)


def _connection(scope: dict[str, Any]) -> MagicMock:
    connection = MagicMock()
    connection.scope = scope
    connection.session = scope.get("session")
    return connection


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        pytest.param({}, False, id="absent"),
        pytest.param({"session": None}, False, id="none"),
        pytest.param({"session": Empty}, False, id="empty-sentinel"),
        pytest.param({"session": MappingProxyType({})}, False, id="read-only-mapping"),
        pytest.param({"session": {}}, True, id="writable-dict"),
    ],
)
def test_has_redirect_state_transport_requires_writable_session_dict(scope: dict[str, Any], expected: bool) -> None:
    connection = _connection(scope)

    assert has_redirect_state_transport(connection) is expected


def test_persist_transient_state_without_transport_consumes_and_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    connection = _connection({})
    stage_flash(connection, "Saved", "success")

    with caplog.at_level(logging.WARNING, logger="litestar_vite"):
        first_result = persist_transient_state_for_redirect(connection)
        second_result = persist_transient_state_for_redirect(connection)

    assert first_result == RedirectStatePersistence(had_pending=True, persisted=False)
    assert second_result == RedirectStatePersistence(had_pending=False, persisted=False)
    assert peek_transient_state(connection) is None
    assert len(caplog.records) == 1
    assert "no writable Litestar session" in caplog.text
    assert "session middleware covers this route" in caplog.text
    assert "CookieBackendConfig" not in caplog.text


def test_persist_transient_state_writes_session_handoff_keys_without_warning(caplog: pytest.LogCaptureFixture) -> None:
    session: dict[str, Any] = {}
    connection = _connection({"session": session})
    stage_shared(connection, "auth", {"user": "Ada"})
    stage_flash(connection, "Saved", "success")
    stage_error(connection, "email", "Invalid email")
    stage_clear_history(connection)

    with caplog.at_level(logging.WARNING, logger="litestar_vite"):
        result = persist_transient_state_for_redirect(connection)

    assert result == RedirectStatePersistence(had_pending=True, persisted=True)
    assert session == {
        "_shared": {"auth": {"user": "Ada"}},
        "_messages": [{"category": "success", "message": "Saved"}],
        "_errors": {"email": "Invalid email"},
        "_inertia_clear_history": True,
    }
    assert peek_transient_state(connection) is None
    assert caplog.records == []


def test_persist_transient_state_reports_unmaterializable_shared_keys_once(caplog: pytest.LogCaptureFixture) -> None:
    async def load_slow() -> dict[str, int]:
        return {"value": 1}

    session: dict[str, Any] = {}
    connection = _connection({"session": session})
    stage_shared(connection, "ready", {"value": 2})
    stage_shared(connection, "slow", defer("slow", load_slow))
    stage_flash(connection, "Saved", "success")

    with caplog.at_level(logging.WARNING, logger="litestar_vite"):
        first_result = persist_transient_state_for_redirect(connection)
        second_result = persist_transient_state_for_redirect(connection)

    assert first_result == RedirectStatePersistence(had_pending=True, persisted=False, dropped_keys=("slow",))
    assert second_result == RedirectStatePersistence(had_pending=False, persisted=False)
    assert session == {"_shared": {"ready": {"value": 2}}, "_messages": [{"category": "success", "message": "Saved"}]}
    assert peek_transient_state(connection) is None
    assert len(caplog.records) == 1
    assert "slow" in caplog.text
    assert "Async shared props cannot cross redirects" in caplog.text
    assert "direct Inertia response" in caplog.text
