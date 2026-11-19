import logging
from types import MappingProxyType
from typing import Any
from unittest.mock import MagicMock

import pytest
from litestar import Request, get, post
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.testing import create_test_client
from litestar.types import Empty

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin, InertiaRedirect, flash
from litestar_vite.inertia.helpers import defer, once, optional
from litestar_vite.inertia.state import (
    MAX_SESSION_FLASH_MESSAGES,
    RedirectStatePersistence,
    get_prop_eval_cache,
    has_redirect_state_transport,
    peek_transient_state,
    persist_transient_state_for_redirect,
    stage_clear_history,
    stage_error,
    stage_flash,
    stage_shared,
)
from litestar_vite.plugin import VitePlugin


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


def test_get_prop_eval_cache_is_scoped_per_connection() -> None:
    """Prop evaluation caches are isolated per ASGI scope and reused within the same scope."""
    first = _connection({})
    second = _connection({})

    cache_first = get_prop_eval_cache(first)
    cache_first[1] = ("prop", "value")

    assert get_prop_eval_cache(first) is cache_first
    assert get_prop_eval_cache(second) == {}
    assert get_prop_eval_cache(second) is not cache_first


@pytest.mark.parametrize("prop_kind", ["once", "defer", "optional"])
def test_persist_transient_state_materializes_shared_prop_without_mutating_instance(prop_kind: str) -> None:
    """Redirect materialization uses the per-request cache and never mutates shared prop instances."""
    counter = 0

    def next_value() -> int:
        nonlocal counter
        counter += 1
        return counter

    shared_prop: Any = (
        once("shared", next_value)
        if prop_kind == "once"
        else defer("shared", next_value)
        if prop_kind == "defer"
        else optional("shared", next_value)
    )

    session_one: dict[str, Any] = {}
    conn_one = _connection({"session": session_one})
    stage_shared(conn_one, "shared", shared_prop)
    result_one = persist_transient_state_for_redirect(conn_one)

    session_two: dict[str, Any] = {}
    conn_two = _connection({"session": session_two})
    stage_shared(conn_two, "shared", shared_prop)
    result_two = persist_transient_state_for_redirect(conn_two)

    assert result_one == RedirectStatePersistence(had_pending=True, persisted=True)
    assert result_two == RedirectStatePersistence(had_pending=True, persisted=True)
    assert session_one["_shared"] == {"shared": 1}
    assert session_two["_shared"] == {"shared": 2}
    assert shared_prop._evaluated is False


def test_persist_transient_state_caps_unconsumed_session_flashes_at_twenty() -> None:
    """Repeated unconsumed redirects retain only the 20 most recent flash entries in order."""
    session: dict[str, Any] = {}

    for index in range(1, 26):
        connection = _connection({"session": session})
        stage_flash(connection, f"msg-{index}", "info")
        result = persist_transient_state_for_redirect(connection)
        assert result == RedirectStatePersistence(had_pending=True, persisted=True)

    assert MAX_SESSION_FLASH_MESSAGES == 20
    assert len(session["_messages"]) == 20
    assert session["_messages"] == [{"category": "info", "message": f"msg-{index}"} for index in range(6, 26)]


def test_persist_transient_state_deduplicates_unconsumed_error_flashes_and_preserves_cap() -> None:
    """Repeated unconsumed error flashes replace earlier duplicates and move to the tail."""
    session: dict[str, Any] = {}

    for index in range(1, 11):
        conn_err = _connection({"session": session})
        stage_flash(conn_err, "Validation failed", "error")
        persist_transient_state_for_redirect(conn_err)

        conn_info = _connection({"session": session})
        stage_flash(conn_info, f"info-{index}", "info")
        persist_transient_state_for_redirect(conn_info)

    conn_distinct_err = _connection({"session": session})
    stage_flash(conn_distinct_err, "Another error", "error")
    persist_transient_state_for_redirect(conn_distinct_err)

    conn_repeat_err = _connection({"session": session})
    stage_flash(conn_repeat_err, "Validation failed", "error")
    persist_transient_state_for_redirect(conn_repeat_err)

    messages = session["_messages"]
    assert len(messages) <= MAX_SESSION_FLASH_MESSAGES
    assert [m for m in messages if m == {"category": "error", "message": "Validation failed"}] == [
        {"category": "error", "message": "Validation failed"}
    ]
    assert messages[-1] == {"category": "error", "message": "Validation failed"}
    assert {"category": "error", "message": "Another error"} in messages
    assert [m["message"] for m in messages if m["category"] == "info"] == [f"info-{index}" for index in range(1, 11)]


def test_repeated_error_redirects_deduplicate_flashes_over_http(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: Any
) -> None:
    """Repeated error redirect responses keep one deduplicated error entry at the tail within the 20-entry cap."""

    info_counter = 0

    @post("/submit-error")
    async def submit_error(request: Request[Any, Any, Any]) -> InertiaRedirect:
        flash(request, "Validation failed", "error")
        return InertiaRedirect(request, redirect_to="/target")

    @post("/submit-info")
    async def submit_info(request: Request[Any, Any, Any]) -> InertiaRedirect:
        nonlocal info_counter
        info_counter += 1
        flash(request, f"notice-{info_counter}", "info")
        return InertiaRedirect(request, redirect_to="/target")

    @get("/target", component="Target")
    async def target(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"ok": True}

    with create_test_client(
        route_handlers=[submit_error, submit_info, target],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        for _ in range(22):
            resp_err = client.post("/submit-error", follow_redirects=False)
            assert resp_err.status_code == 303
            resp_info = client.post("/submit-info", follow_redirects=False)
            assert resp_info.status_code == 303

        resp_final_err = client.post("/submit-error", follow_redirects=False)
        assert resp_final_err.status_code == 303

        page = client.get("/target", headers={InertiaHeaders.ENABLED.value: "true"})
        assert page.status_code == 200
        flashed = page.json()["flash"]
        assert flashed["error"] == ["Validation failed"]
        assert len(flashed["info"]) == 19
        assert flashed["info"] == [f"notice-{index}" for index in range(4, 23)]
