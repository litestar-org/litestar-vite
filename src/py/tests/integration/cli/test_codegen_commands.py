"""Tests for type generation CLI commands."""

from pathlib import Path

from litestar import Litestar, get
from litestar.serialization import decode_json, encode_json, get_serializer

from litestar_vite.codegen import generate_routes_json
from litestar_vite.config import TypeGenConfig, ViteConfig
from litestar_vite.plugin import VitePlugin


def test_export_routes_integration(tmp_path: Path) -> None:
    """Test routes export integration."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users_handler() -> list[str]:
        return ["user1", "user2"]

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user_handler(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard_handler() -> dict[str, str]:
        return {}

    config = ViteConfig(
        types=TypeGenConfig(openapi_path=tmp_path / "openapi.json", routes_path=tmp_path / "routes.json")
    )
    plugin = VitePlugin(config=config)

    app = Litestar(route_handlers=[list_users_handler, get_user_handler, dashboard_handler], plugins=[plugin])

    # Generate routes
    routes_data = generate_routes_json(app, include_components=True)

    # Write to file
    output_path = tmp_path / "routes.json"
    output_path.write_bytes(encode_json(routes_data))

    assert output_path.exists()

    # Verify content
    loaded = decode_json(output_path.read_bytes())
    assert "routes" in loaded
    routes = loaded["routes"]

    # Should have our routes
    assert any("list_users" in name or "users" in name.lower() for name in routes)


def test_export_schema_integration(tmp_path: Path) -> None:
    """Test schema export integration."""

    @get("/test", sync_to_thread=False)
    def test_handler() -> dict[str, str]:
        return {}

    config = ViteConfig(types=TypeGenConfig(openapi_path=tmp_path / "openapi.json"))
    plugin = VitePlugin(config=config)

    app = Litestar(route_handlers=[test_handler], plugins=[plugin])

    # Get the schema
    schema = app.openapi_schema.to_schema()

    # Write to file
    output_path = tmp_path / "schema.json"
    serializer = get_serializer(app.type_encoders)
    output_path.write_bytes(encode_json(schema, serializer=serializer))

    assert output_path.exists()

    # Verify it's valid JSON
    loaded = decode_json(output_path.read_bytes())
    assert "openapi" in loaded or "info" in loaded


def test_routes_with_filters(tmp_path: Path) -> None:
    """Test route generation with filters."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users_handler() -> list[str]:
        return []

    @get("/posts", name="list_posts", sync_to_thread=False)
    def list_posts_handler() -> list[str]:
        return []

    @get("/admin/settings", name="admin_settings", sync_to_thread=False)
    def admin_settings_handler() -> dict[str, str]:
        return {}

    app = Litestar([list_users_handler, list_posts_handler, admin_settings_handler])

    # Test with 'only' filter
    routes_data = generate_routes_json(app, only=["users"])
    routes = routes_data["routes"]
    assert any("user" in name.lower() for name in routes)

    # Test with 'exclude' filter
    routes_data = generate_routes_json(app, exclude=["admin"])
    routes = routes_data["routes"]
    assert not any("admin" in name.lower() for name in routes)


def test_export_routes_typescript_integration(tmp_path: Path) -> None:
    """Test TypeScript routes export integration."""
    from litestar_vite.codegen import generate_routes_ts

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users_handler() -> list[str]:
        return ["user1", "user2"]

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user_handler(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard_handler() -> dict[str, str]:
        return {}

    config = ViteConfig(types=TypeGenConfig(generate_routes=True, routes_ts_path=tmp_path / "routes.ts"))
    plugin = VitePlugin(config=config)

    app = Litestar(route_handlers=[list_users_handler, get_user_handler, dashboard_handler], plugins=[plugin])

    # Generate TypeScript routes
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Write to file
    output_path = tmp_path / "routes.ts"
    output_path.write_text(ts_content, encoding="utf-8")

    assert output_path.exists()

    # Verify content structure
    content = output_path.read_text()
    assert "export type RouteName =" in content
    assert "export const routeDefinitions = {" in content
    assert "export function route<" in content
    assert "'list_users'" in content
    assert "'get_user'" in content
    assert "'dashboard'" in content
    assert "component: 'Dashboard/Index'" in content
    assert "user_id: number" in content  # Type inference from OpenAPI


def test_typescript_routes_with_config(tmp_path: Path) -> None:
    """Test TypeScript routes generation respects TypeGenConfig."""
    from litestar_vite.codegen import generate_routes_ts

    @get("/test", name="test_route", sync_to_thread=False)
    def test_handler() -> str:
        return "test"

    config = ViteConfig(
        types=TypeGenConfig(generate_routes=True, routes_ts_path=tmp_path / "src" / "generated" / "routes.ts")
    )
    plugin = VitePlugin(config=config)

    app = Litestar(route_handlers=[test_handler], plugins=[plugin])

    # Generate routes
    ts_content = generate_routes_ts(app)

    # Verify output location from config
    assert isinstance(config.types, TypeGenConfig)
    assert config.types.routes_ts_path == tmp_path / "src" / "generated" / "routes.ts"

    # Write to configured path
    output_path = config.types.routes_ts_path
    assert output_path is not None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ts_content, encoding="utf-8")

    assert output_path.exists()
    content = output_path.read_text()
    assert "'test_route'" in content
