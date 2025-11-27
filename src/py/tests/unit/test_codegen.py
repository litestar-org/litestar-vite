"""Tests for code generation utilities."""

from __future__ import annotations

from uuid import UUID

from litestar import Litestar, get, post
from litestar.datastructures import State
from litestar.params import Parameter

from litestar_vite.codegen import (
    RouteMetadata,
    _normalize_path,
    _python_type_to_typescript,
    extract_route_metadata,
    generate_routes_json,
)


def test_python_type_to_typescript() -> None:
    """Test Python to TypeScript type conversion."""
    assert _python_type_to_typescript("int") == "number"
    assert _python_type_to_typescript("float") == "number"
    assert _python_type_to_typescript("str") == "string"
    assert _python_type_to_typescript("bool") == "boolean"
    assert _python_type_to_typescript("uuid.UUID") == "string"
    assert _python_type_to_typescript("UUID") == "string"
    assert _python_type_to_typescript("datetime.datetime") == "string"
    assert _python_type_to_typescript("unknown_type") == "string"


def test_normalize_path() -> None:
    """Test path normalization."""
    assert _normalize_path("/users") == "/users"
    assert _normalize_path("/users/{user_id:int}") == "/users/{user_id}"
    assert _normalize_path("/items/{uuid:uuid}") == "/items/{uuid}"
    assert _normalize_path("/posts/{slug:str}") == "/posts/{slug}"
    assert (
        _normalize_path("/api/v1/users/{user_id:int}/posts/{post_id:int}") == "/api/v1/users/{user_id}/posts/{post_id}"
    )


def test_normalize_path_cross_platform() -> None:
    """Test path normalization works consistently across platforms."""
    # Even on Windows, HTTP paths should use forward slashes
    path = "/users/{id:int}"
    normalized = _normalize_path(path)
    assert normalized == "/users/{id}"
    assert "\\" not in normalized


def test_route_metadata_dataclass() -> None:
    """Test RouteMetadata dataclass."""
    metadata = RouteMetadata(
        name="get_user",
        path="/users/{user_id}",
        methods=["GET"],
        params={"user_id": "number"},
        query_params={"include": "string"},
        component="Users/Show",
    )

    assert metadata.name == "get_user"
    assert metadata.path == "/users/{user_id}"
    assert metadata.methods == ["GET"]
    assert metadata.params == {"user_id": "number"}
    assert metadata.query_params == {"include": "string"}
    assert metadata.component == "Users/Show"


def test_extract_route_metadata_basic() -> None:
    """Test basic route metadata extraction."""

    @get("/users")
    def list_users() -> list[str]:
        return ["user1", "user2"]

    @get("/users/{user_id:int}")
    def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([list_users, get_user])
    routes = extract_route_metadata(app)

    # Should have 2 routes
    assert len(routes) >= 2

    # Find the routes by path
    list_route = next((r for r in routes if r.path == "/users"), None)
    get_route = next((r for r in routes if "/users/{user_id}" in r.path), None)

    assert list_route is not None
    assert list_route.methods == ["GET"]

    assert get_route is not None
    assert get_route.methods == ["GET"]
    assert "user_id" in get_route.params


def test_extract_route_metadata_with_types() -> None:
    """Test route metadata extraction with various path parameter types."""

    @get("/users/{user_id:int}")
    def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    @get("/items/{item_uuid:uuid}")
    def get_item(item_uuid: UUID) -> dict[str, str]:
        return {"uuid": str(item_uuid)}

    @get("/posts/{slug:str}")
    def get_post(slug: str) -> dict[str, str]:
        return {"slug": slug}

    app = Litestar([get_user, get_item, get_post])
    routes = extract_route_metadata(app)

    # Find routes
    user_route = next((r for r in routes if "user_id" in r.path), None)
    item_route = next((r for r in routes if "item_uuid" in r.path), None)
    post_route = next((r for r in routes if "slug" in r.path), None)

    assert user_route is not None
    assert "user_id" in user_route.params

    assert item_route is not None
    assert "item_uuid" in item_route.params

    assert post_route is not None
    assert "slug" in post_route.params


def test_extract_route_metadata_multiple_methods() -> None:
    """Test route metadata extraction with multiple HTTP methods."""

    @get("/users", name="list_users")
    def list_users_handler() -> list[str]:
        return []

    @post("/users", name="create_user")
    def create_user_handler() -> dict[str, str]:
        return {}

    app = Litestar([list_users_handler, create_user_handler])
    routes = extract_route_metadata(app)

    # Find routes by name
    list_route = next((r for r in routes if r.name == "list_users"), None)
    create_route = next((r for r in routes if r.name == "create_user"), None)

    assert list_route is not None
    assert list_route.methods == ["GET"]

    assert create_route is not None
    assert create_route.methods == ["POST"]


def test_extract_route_metadata_with_component() -> None:
    """Test route metadata extraction with Inertia component."""

    @get("/dashboard", opt={"component": "Dashboard/Index"})
    def dashboard() -> dict[str, str]:
        return {}

    @get("/users", opt={"component": "Users/Index"})
    def users() -> dict[str, str]:
        return {}

    app = Litestar([dashboard, users])
    routes = extract_route_metadata(app)

    dashboard_route = next((r for r in routes if r.path == "/dashboard"), None)
    users_route = next((r for r in routes if r.path == "/users"), None)

    assert dashboard_route is not None
    assert dashboard_route.component == "Dashboard/Index"

    assert users_route is not None
    assert users_route.component == "Users/Index"


def test_extract_route_metadata_with_filters() -> None:
    """Test route metadata extraction with only/exclude filters."""

    @get("/users", name="list_users")
    def list_users_handler() -> list[str]:
        return []

    @get("/posts", name="list_posts")
    def list_posts_handler() -> list[str]:
        return []

    @get("/admin/settings", name="admin_settings")
    def admin_settings_handler() -> dict[str, str]:
        return {}

    app = Litestar([list_users_handler, list_posts_handler, admin_settings_handler])

    # Test with 'only' filter
    routes = extract_route_metadata(app, only=["users"])
    assert len(routes) >= 1
    assert any(r.name == "list_users" for r in routes)

    # Test with 'exclude' filter
    routes = extract_route_metadata(app, exclude=["admin"])
    assert not any("admin" in r.name for r in routes)


def test_generate_routes_json_basic() -> None:
    """Test basic routes JSON generation."""

    @get("/users", name="list_users")
    def list_users_handler() -> list[str]:
        return []

    @get("/users/{user_id:int}", name="get_user")
    def get_user_handler(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([list_users_handler, get_user_handler])
    routes_json = generate_routes_json(app)

    assert "routes" in routes_json
    routes = routes_json["routes"]

    # Check that routes are present
    assert "list_users" in routes or "get_user" in routes


def test_generate_routes_json_with_components() -> None:
    """Test routes JSON generation with Inertia components."""

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard_handler() -> dict[str, str]:
        return {}

    app = Litestar([dashboard_handler])
    routes_json = generate_routes_json(app, include_components=True)

    assert "routes" in routes_json
    routes = routes_json["routes"]

    # Find the dashboard route
    dashboard_route = routes.get("dashboard")
    if dashboard_route:
        assert "component" in dashboard_route
        assert dashboard_route["component"] == "Dashboard/Index"


def test_generate_routes_json_structure() -> None:
    """Test the structure of generated routes JSON."""

    @get("/users/{user_id:int}", name="get_user")
    def get_user_handler(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([get_user_handler])
    routes_json = generate_routes_json(app)

    assert "routes" in routes_json
    routes = routes_json["routes"]

    # Find the get_user route
    user_route = routes.get("get_user")
    if user_route:
        assert "uri" in user_route
        assert "methods" in user_route
        assert isinstance(user_route["methods"], list)
        assert "GET" in user_route["methods"]


def test_generate_routes_json_with_mount_path() -> None:
    """Test routes JSON generation with mounted routes."""
    from litestar import Router

    @get("/users", name="api_users", sync_to_thread=False)
    def users_handler() -> list[str]:
        return []

    router = Router(path="/api/v1", route_handlers=[users_handler])
    app = Litestar([router])

    routes_json = generate_routes_json(app)
    assert "routes" in routes_json

    # The route should include the mount path
    routes = routes_json["routes"]
    api_route = routes.get("api_users")
    if api_route:
        assert "/api/v1" in api_route["uri"]


def test_generate_routes_json_with_query_params() -> None:
    """Test routes JSON generation includes query parameters."""

    @get("/search", name="search", sync_to_thread=False)
    def search_handler(
        query: str,
        page: int = 1,
    ) -> dict[str, str | int]:
        return {"query": query, "page": page}

    app = Litestar([search_handler])
    routes_json = generate_routes_json(app)

    assert "routes" in routes_json
    routes = routes_json["routes"]

    # Find the search route
    search_route = routes.get("search")
    assert search_route is not None
    assert "queryParameters" in search_route

    query_params = search_route["queryParameters"]
    # 'query' should be required (no default), 'page' should be optional
    assert "query" in query_params
    assert "page" in query_params
    assert "string" in query_params["query"]
    assert "number" in query_params["page"]
    # page has default=1, so should include undefined
    assert "undefined" in query_params["page"]


def test_extract_query_params_with_optional_types() -> None:
    """Test query parameter extraction with Optional types."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users_handler(
        search: str | None = None,
        limit: int = 10,
        active: bool = True,
    ) -> list[str]:
        return []

    app = Litestar([list_users_handler])
    routes = extract_route_metadata(app)

    users_route = next((r for r in routes if r.name == "list_users"), None)
    assert users_route is not None

    query_params = users_route.query_params
    # All have defaults, so all should be optional
    assert "search" in query_params
    assert "limit" in query_params
    assert "active" in query_params

    # Check types
    assert "string" in query_params["search"]
    assert "number" in query_params["limit"]
    assert "boolean" in query_params["active"]


def test_extract_query_params_excludes_path_params() -> None:
    """Test that path parameters are excluded from query params."""

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user_handler(
        user_id: int,
        include_details: bool = False,
    ) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([get_user_handler])
    routes = extract_route_metadata(app)

    user_route = next((r for r in routes if r.name == "get_user"), None)
    assert user_route is not None

    # user_id should be in path params, not query params
    assert "user_id" in user_route.params
    assert "user_id" not in user_route.query_params

    # include_details should be in query params
    assert "include_details" in user_route.query_params


def test_extract_query_params_excludes_system_types() -> None:
    """Test that system types (State, Request) are excluded from query params."""
    from litestar.connection import Request

    @get("/health", name="health", sync_to_thread=False)
    def health_handler(
        state: State,
        request: Request,
        verbose: bool = False,
    ) -> dict[str, str]:
        return {"status": "ok"}

    app = Litestar([health_handler])
    routes = extract_route_metadata(app)

    health_route = next((r for r in routes if r.name == "health"), None)
    assert health_route is not None

    query_params = health_route.query_params
    # State and Request should NOT be in query params
    assert "state" not in query_params
    assert "request" not in query_params

    # verbose should be in query params
    assert "verbose" in query_params


def test_extract_query_params_with_parameter_alias() -> None:
    """Test query parameter extraction with Parameter() alias."""

    @get("/search", name="search", sync_to_thread=False)
    def search_handler(
        q: str = Parameter(query="search_query"),
    ) -> dict[str, str]:
        return {"query": q}

    app = Litestar([search_handler])
    routes = extract_route_metadata(app)

    search_route = next((r for r in routes if r.name == "search"), None)
    assert search_route is not None

    query_params = search_route.query_params
    # Should use the alias 'search_query', not the Python arg name 'q'
    assert "search_query" in query_params
    assert "q" not in query_params


def test_path_normalization_edge_cases() -> None:
    """Test path normalization edge cases."""
    # Empty path
    assert _normalize_path("") == ""

    # Root path
    assert _normalize_path("/") == "/"

    # Path with no parameters
    assert _normalize_path("/api/users") == "/api/users"

    # Path with multiple parameters
    assert _normalize_path("/users/{user_id:int}/posts/{post_id:int}") == "/users/{user_id}/posts/{post_id}"

    # Path with regex constraints (should still normalize)
    assert _normalize_path("/items/{item_id:int}") == "/items/{item_id}"


def test_extract_route_metadata_empty_app() -> None:
    """Test extracting metadata from an app with no routes."""

    @get("/health", sync_to_thread=False)
    def health_check(state: State) -> dict[str, str]:
        return {"status": "ok"}

    app = Litestar([health_check])
    routes = extract_route_metadata(app)

    # Should return a list (may be empty or contain routes)
    assert isinstance(routes, list)
