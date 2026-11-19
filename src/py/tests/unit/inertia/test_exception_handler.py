"""Regression tests for Inertia exception handling."""

import logging
from typing import Annotated, Any

import pytest
from litestar import Request, get, post
from litestar.exceptions import (
    HTTPException,
    InternalServerException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.params import Body
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.helpers import once, share
from litestar_vite.inertia.response import InertiaBack, InertiaExternalRedirect, InertiaRedirect, InertiaResponse
from litestar_vite.plugin import VitePlugin


async def test_shared_prop_survives_exception_redirect(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    """Exception-produced redirects best-effort materialize shared sync props."""
    calls: list[int] = []
    inertia_plugin.config.redirect_unauthorized_to = "/login"

    def load_auth() -> dict[str, str]:
        calls.append(1)
        return {"user": "Ada"}

    @get("/protected", component="Protected")
    async def protected(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "auth", once("auth", load_auth))
        raise NotAuthorizedException

    @get("/login", component="Login")
    async def login() -> dict[str, Any]:
        return {}

    with create_test_client(
        route_handlers=[protected, login],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/protected", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=True)

    assert response.status_code == 200
    assert response.json()["props"]["auth"] == {"user": "Ada"}
    assert calls == [1]


async def test_production_500_body_omits_exception_detail(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom")
    async def handler() -> None:
        raise RuntimeError("secret db dsn leaked")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert "secret db dsn leaked" not in response.text
    assert "Internal Server Error" in response.text


async def test_inertia_500_flash_and_body_omit_detail_in_production(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom", component="Boom")
    async def handler() -> dict[str, str]:
        raise RuntimeError("secret db dsn leaked")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 500
    body = response.json()
    assert body["props"]["message"] == "Internal Server Error"
    assert "secret db dsn leaked" not in response.text


async def test_debug_500_still_includes_detail(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom")
    async def handler() -> None:
        raise RuntimeError("debug detail visible")

    with create_test_client(
        route_handlers=[handler],
        debug=True,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert "debug detail visible" in response.text


async def test_inertia_error_without_route_component_avoids_null_component(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig[Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    @get("/api/data")
    async def handler() -> dict[str, str]:
        raise RuntimeError("api exploded")

    with (
        caplog.at_level(logging.ERROR, logger="litestar_vite.inertia"),
        create_test_client(
            route_handlers=[handler],
            debug=False,
            logging_config=None,
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client,
    ):
        response = client.get("/api/data", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 500
    body = response.json()
    assert "component" not in body
    assert body == {"status_code": 500, "detail": "Internal Server Error"}
    assert "api exploded" not in response.text
    assert len(caplog.records) == 1
    assert "api exploded" in caplog.text


async def test_inertia_error_with_component_still_renders_page(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/page", component="Page")
    async def handler() -> dict[str, str]:
        raise RuntimeError("page exploded")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/page", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 500
    body = response.json()
    assert body["component"] == "Page"
    assert body["props"]["message"] == "Internal Server Error"


async def test_all_validation_errors_are_flashed(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    """Every validation error in extra is flashed to the client."""

    @get("/register", component="Register")
    async def register_handler() -> dict[str, Any]:
        raise ValidationException(
            detail="Validation failed",
            extra=[
                {"key": "name", "message": "Value error, name is required"},
                {"key": "email", "message": "Value error, email is invalid"},
                {"key": "age", "message": "Value error, age must be positive"},
            ],
        )

    @get("/form", component="Form")
    async def form_handler() -> dict[str, Any]:
        return {}

    with create_test_client(
        route_handlers=[register_handler, form_handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get(
            "/register",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/form"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    errors = response.json()["props"]["errors"]
    assert errors == {
        "root.name": "Value error, name is required",
        "root.email": "Value error, email is invalid",
        "root.age": "Value error, age must be positive",
    }


async def test_field_err_re_still_wins_per_entry(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    """FIELD_ERR_RE regex extract wins over root.<key> per entry."""

    @get("/register", component="Register")
    async def register_handler() -> dict[str, Any]:
        raise ValidationException(
            detail="Validation failed",
            extra=[
                {"key": "user_email", "message": "Validation error for field `email`"},
                {"key": "user_name", "message": "Validation error for field `name`"},
            ],
        )

    @get("/form", component="Form")
    async def form_handler() -> dict[str, Any]:
        return {}

    with create_test_client(
        route_handlers=[register_handler, form_handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get(
            "/register",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/form"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    errors = response.json()["props"]["errors"]
    assert errors == {"email": "Validation error for field `email`", "name": "Validation error for field `name`"}


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail", "expect_masked"),
    [
        (
            ValidationException(detail="invalid payload", extra=[{"key": "name", "message": "name is required"}]),
            400,
            "invalid payload",
            False,
        ),
        (NotAuthorizedException(detail="auth required"), 401, "auth required", False),
        (PermissionDeniedException(detail="forbidden"), 403, "forbidden", False),
        (NotFoundException(detail="missing item"), 404, "missing item", False),
        (
            HTTPException(status_code=503, detail="upstream secret", extra={"host": "db.internal"}),
            503,
            "Internal Server Error",
            True,
        ),
    ],
)
async def test_non_component_route_keeps_default_json_response_with_inertia_header(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig[Any],
    caplog: pytest.LogCaptureFixture,
    exc: Exception,
    expected_status: int,
    expected_detail: str,
    expect_masked: bool,
) -> None:
    """Matched non-component routes return Litestar JSON errors without flashing or redirecting."""
    inertia_plugin.config.redirect_unauthorized_to = "/login"
    inertia_plugin.config.redirect_404 = "/"

    @get("/api/data")
    async def api_handler() -> dict[str, str]:
        raise exc

    @get("/api/session")
    async def session_handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return dict(request.session)

    with (
        caplog.at_level(logging.ERROR, logger="litestar_vite.inertia"),
        create_test_client(
            route_handlers=[api_handler, session_handler],
            debug=False,
            logging_config=None,
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client,
    ):
        response = client.get(
            "/api/data",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/form"},
            follow_redirects=False,
        )
        session_response = client.get("/api/session")

    assert response.status_code == expected_status
    assert "location" not in response.headers
    body = response.json()
    assert "component" not in body
    assert body["status_code"] == expected_status
    assert body["detail"] == expected_detail
    session_data = session_response.json()
    assert "_messages" not in session_data
    assert "_errors" not in session_data
    if expect_masked:
        assert "upstream secret" not in response.text
        assert "db.internal" not in response.text
        assert "extra" not in body
        assert len(caplog.records) == 1
        assert "upstream secret" in caplog.text
    else:
        assert caplog.records == []


async def test_non_component_post_validation_error_keeps_json_response_with_inertia_header(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    """Matched non-component POST routes return 400 JSON on body validation failure."""

    @post("/api/items")
    async def create_item(data: Annotated[dict[str, int], Body()]) -> dict[str, int]:
        return data

    @get("/api/session")
    async def session_handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return dict(request.session)

    with create_test_client(
        route_handlers=[create_item, session_handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/api/items",
            json={"count": "invalid"},
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/form"},
            follow_redirects=False,
        )
        session_response = client.get("/api/session")

    assert response.status_code == 400
    assert "location" not in response.headers
    body = response.json()
    assert "component" not in body
    assert body["status_code"] == 400
    assert "_messages" not in session_response.json()
    assert "_errors" not in session_response.json()


@pytest.mark.parametrize(("method", "path"), [("GET", "/missing"), ("POST", "/only-get")])
async def test_unmatched_routes_retain_redirect_404_with_inertia_header(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any], method: str, path: str
) -> None:
    """Unmatched 404 and 405 requests with X-Inertia still follow redirect_404."""
    inertia_plugin.config.redirect_404 = "/"

    @get("/", component="Home")
    async def home() -> dict[str, str]:
        return {"page": "home"}

    @get("/only-get", component="OnlyGet")
    async def only_get() -> dict[str, str]:
        return {"page": "only-get"}

    with create_test_client(
        route_handlers=[home, only_get],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.request(method, path, headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)

    assert response.status_code in {303, 307}
    assert response.headers["location"] == "/"


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (HTTPException(status_code=500, detail="sql detail", extra={"sql": "SELECT 1"}), 500),
        (InternalServerException(detail="sql detail"), 500),
        (HTTPException(status_code=503, detail="sql detail", extra={"host": "db.internal"}), 503),
    ],
)
@pytest.mark.parametrize("debug", [False, True])
async def test_component_route_5xx_http_exception_masking_and_logging(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig[Any],
    caplog: pytest.LogCaptureFixture,
    exc: HTTPException,
    expected_status: int,
    debug: bool,
) -> None:
    """Component routes mask 5xx HTTPException details and extras when debug is False."""

    @get("/page", component="Page")
    async def page_handler() -> dict[str, str]:
        raise exc

    with (
        caplog.at_level(logging.ERROR, logger="litestar_vite.inertia"),
        create_test_client(
            route_handlers=[page_handler],
            debug=debug,
            logging_config=None,
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client,
    ):
        response = client.get("/page", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == expected_status
    body = response.json()
    assert body["component"] == "Page"
    props = body["props"]
    if debug:
        assert props["message"] == "sql detail"
        assert caplog.records == []
        if exc.extra is not None:
            assert props["extra"] == exc.extra
    else:
        assert props["message"] == "Internal Server Error"
        assert "extra" not in props
        assert "sql detail" not in response.text
        assert "SELECT 1" not in response.text
        assert "db.internal" not in response.text
        assert body.get("flash", {}).get("error") == ["Internal Server Error"]
        assert len(caplog.records) == 1
        assert "sql detail" in caplog.text


@pytest.mark.parametrize("debug", [False, True])
async def test_non_component_route_503_debug_toggle(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig[Any],
    caplog: pytest.LogCaptureFixture,
    debug: bool,
) -> None:
    """Non-component 503 HTTPExceptions mask details in production and expose them in debug."""

    @get("/api/upstream")
    async def upstream_handler() -> dict[str, str]:
        raise HTTPException(status_code=503, detail="upstream secret", extra={"host": "db.internal"})

    with (
        caplog.at_level(logging.ERROR, logger="litestar_vite.inertia"),
        create_test_client(
            route_handlers=[upstream_handler],
            debug=debug,
            logging_config=None,
            plugins=[inertia_plugin, vite_plugin],
            template_config=template_config,
            middleware=[ServerSideSessionConfig().middleware],
            stores={"sessions": MemoryStore()},
            raise_server_exceptions=False,
        ) as client,
    ):
        response = client.get("/api/upstream", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 503
    body = response.json()
    assert "component" not in body
    assert body["status_code"] == 503
    if debug:
        assert body["detail"] == "upstream secret"
        assert body["extra"] == {"host": "db.internal"}
        assert caplog.records == []
    else:
        assert body["detail"] == "Internal Server Error"
        assert "extra" not in body
        assert "upstream secret" not in response.text
        assert len(caplog.records) == 1
        assert "upstream secret" in caplog.text


async def test_non_component_generic_container_return_type_stays_json(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    """Generic container return annotations containing InertiaResponse do not opt into Inertia."""

    @get("/api/container")
    async def container_handler() -> dict[str, InertiaResponse[Any]]:
        raise NotFoundException(detail="missing container")

    inertia_plugin.config.redirect_404 = "/"

    with create_test_client(
        route_handlers=[container_handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/api/container", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)

    assert response.status_code == 404
    assert "location" not in response.headers
    assert response.json() == {"status_code": 404, "detail": "missing container"}


@pytest.mark.parametrize("path", ["/users", "/users-opt", "/users-response", "/users-external"])
async def test_inertia_mutation_handler_validation_error_retains_inertia_back(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any], path: str
) -> None:
    """Inertia mutation routes without component= still flash errors and redirect back."""

    @post("/users")
    async def create_user(
        request: Request[Any, Any, Any], data: Annotated[dict[str, int], Body()]
    ) -> InertiaRedirect | InertiaBack:
        return InertiaRedirect(request, redirect_to="/form")

    @post("/users-opt", inertia=True)
    async def create_user_opt(data: Annotated[dict[str, int], Body()]) -> dict[str, int]:
        return data

    @post("/users-response")
    async def create_user_response(data: Annotated[dict[str, int], Body()]) -> InertiaResponse[dict[str, int]]:
        return InertiaResponse(content=data, component="Form")

    @post("/users-external")
    async def create_user_external(
        request: Request[Any, Any, Any], data: Annotated[dict[str, int], Body()]
    ) -> InertiaExternalRedirect:
        return InertiaExternalRedirect(request, redirect_to="https://example.com")

    @get("/form", component="Form")
    async def form_handler() -> dict[str, Any]:
        return {}

    with create_test_client(
        route_handlers=[create_user, create_user_opt, create_user_response, create_user_external, form_handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        redirect_response = client.post(
            path,
            json={"age": "not-an-int"},
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/form"},
            follow_redirects=False,
        )
        assert redirect_response.status_code == 303
        assert redirect_response.headers["location"] == "http://testserver.local/form"

        form_response = client.get("/form", headers={InertiaHeaders.ENABLED.value: "true"})

    assert form_response.status_code == 200
    form_body = form_response.json()
    assert form_body["props"]["errors"]
    assert form_body["flash"]["error"]


@pytest.mark.parametrize(("path", "expected_component"), [("/plain-page", "PlainPage"), ("/plain-api", None)])
async def test_plain_request_class_respects_route_component_scoping(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig[Any],
    path: str,
    expected_component: str | None,
) -> None:
    """Plain Request instances resolve route components via InertiaDetails when scoping errors."""

    @get("/plain-page", component="PlainPage")
    async def page_handler() -> dict[str, str]:
        raise NotFoundException(detail="missing page")

    @get("/plain-api")
    async def api_handler() -> dict[str, str]:
        raise NotFoundException(detail="missing api")

    with create_test_client(
        route_handlers=[page_handler, api_handler],
        debug=False,
        request_class=Request,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get(path, headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 404
    body = response.json()
    if expected_component is not None:
        assert body["component"] == expected_component
        assert body["props"]["message"] == "missing page"
    else:
        assert "component" not in body
        assert body == {"status_code": 404, "detail": "missing api"}
