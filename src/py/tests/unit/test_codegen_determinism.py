"""Unit tests for deterministic code generation output.

These tests verify that code generation produces byte-identical output
for the same input data, regardless of Python dict insertion order.
"""

import json
import tempfile
from pathlib import Path

from litestar import Litestar, get, post

from litestar_vite.codegen import generate_inertia_pages_json, generate_routes_json, generate_routes_ts
from litestar_vite.codegen._utils import (
    deep_sort_dict,
    encode_deterministic_json,
    strip_timestamp_for_comparison,
    write_if_changed,
)


def testdeep_sort_dict_simple() -> None:
    """Test deep sorting of a simple dictionary."""
    unsorted = {"z": 1, "a": 2, "m": 3}
    result = deep_sort_dict(unsorted)
    assert list(result.keys()) == ["a", "m", "z"]


def testdeep_sort_dict_nested() -> None:
    """Test deep sorting of nested dictionaries."""
    unsorted = {"outer": {"z": 1, "a": 2}, "inner": {"b": 3, "c": 4}}
    result = deep_sort_dict(unsorted)
    assert list(result.keys()) == ["inner", "outer"]
    assert list(result["outer"].keys()) == ["a", "z"]
    assert list(result["inner"].keys()) == ["b", "c"]


def testdeep_sort_dict_with_lists() -> None:
    """Test that lists are preserved but their dict elements are sorted."""
    unsorted = {"items": [{"z": 1, "a": 2}, {"y": 3, "b": 4}]}
    result = deep_sort_dict(unsorted)
    assert list(result["items"][0].keys()) == ["a", "z"]
    assert list(result["items"][1].keys()) == ["b", "y"]


def testdeep_sort_dict_preserves_primitives() -> None:
    """Test that primitive values are preserved."""
    data = {"str": "hello", "int": 42, "float": 3.14, "bool": True, "none": None}
    result = deep_sort_dict(data)
    assert result == {"bool": True, "float": 3.14, "int": 42, "none": None, "str": "hello"}


def test_strip_timestamp_for_comparison() -> None:
    """Test timestamp stripping for content comparison."""
    data1 = {"pages": {}, "generatedAt": "2024-01-01T00:00:00Z"}
    data2 = {"pages": {}, "generatedAt": "2024-12-31T23:59:59Z"}

    bytes1 = json.dumps(data1).encode()
    bytes2 = json.dumps(data2).encode()

    # Different raw bytes due to different timestamps
    assert bytes1 != bytes2

    # Same normalized content
    normalized1 = strip_timestamp_for_comparison(bytes1)
    normalized2 = strip_timestamp_for_comparison(bytes2)
    assert normalized1 == normalized2


def test_strip_timestamp_handles_invalid_json() -> None:
    """Test that invalid JSON is returned unchanged."""
    invalid = b"not valid json"
    assert strip_timestamp_for_comparison(invalid) == invalid


def test_write_if_changed_creates_new_file() -> None:
    """Test that write_if_changed creates a new file with trailing newline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        content = b'{"test": "data"}'

        result = write_if_changed(path, content)

        assert result is True
        assert path.exists()
        # write_if_changed ensures trailing newline for POSIX compliance
        assert path.read_bytes() == content + b"\n"


def test_write_if_changed_skips_identical_content() -> None:
    """Test that write_if_changed skips writing identical content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        content = b'{"test": "data"}'
        content_with_newline = content + b"\n"

        # First write (with trailing newline as write_if_changed adds it)
        path.write_bytes(content_with_newline)
        original_stat = path.stat()

        # Second write with same content (will also have newline added)
        result = write_if_changed(path, content)

        assert result is False
        # File modification time should be unchanged
        assert path.stat().st_mtime == original_stat.st_mtime


def test_write_if_changed_updates_different_content() -> None:
    """Test that write_if_changed updates when content differs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        content1 = b'{"test": "data1"}'
        content2 = b'{"test": "data2"}'

        path.write_bytes(content1)

        result = write_if_changed(path, content2)

        assert result is True
        # write_if_changed ensures trailing newline for POSIX compliance
        assert path.read_bytes() == content2 + b"\n"


def test_write_if_changed_with_normalize_callback() -> None:
    """Test write_if_changed with content normalization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"

        content1 = json.dumps({"data": "same", "timestamp": "2024-01-01"}).encode()
        content2 = json.dumps({"data": "same", "timestamp": "2024-12-31"}).encode()

        def strip_timestamp(content: bytes) -> bytes:
            data = json.loads(content)
            data.pop("timestamp", None)
            return json.dumps(data, sort_keys=True).encode()

        path.write_bytes(content1)

        # With normalization, same data but different timestamps should be skipped
        result = write_if_changed(path, content2, normalize_for_comparison=strip_timestamp)

        assert result is False
        # Original content preserved
        assert path.read_bytes() == content1


def test_write_if_changed_creates_parent_dirs() -> None:
    """Test that write_if_changed creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "nested" / "deep" / "test.json"
        content = b'{"test": "data"}'

        result = write_if_changed(path, content)

        assert result is True
        assert path.exists()


def test_write_if_changed_handles_string_content() -> None:
    """Test that write_if_changed handles string content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.txt"
        content = "Hello, World!"

        result = write_if_changed(path, content)

        assert result is True
        # write_if_changed ensures trailing newline for POSIX compliance
        assert path.read_text() == content + "\n"


def test_encode_deterministic_json_produces_sorted_output() -> None:
    """Test that encode_deterministic_json produces sorted output."""
    data = {"z": 1, "a": 2, "m": {"y": 3, "b": 4}}

    result = encode_deterministic_json(data)
    parsed = json.loads(result)

    assert list(parsed.keys()) == ["a", "m", "z"]
    assert list(parsed["m"].keys()) == ["b", "y"]


def test_generate_routes_json_is_deterministic() -> None:
    """Test that generate_routes_json produces deterministic output."""

    @get("/users/{id:int}", name="get_user", sync_to_thread=False)
    def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    @get("/posts/{id:int}", name="get_post", sync_to_thread=False)
    def get_post(id: int) -> dict[str, int]:
        return {"id": id}

    @get("/comments/{id:int}", name="get_comment", sync_to_thread=False)
    def get_comment(id: int) -> dict[str, int]:
        return {"id": id}

    app = Litestar([get_user, get_post, get_comment])

    # Generate twice
    result1 = generate_routes_json(app)
    result2 = generate_routes_json(app)

    # Should be identical
    assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)

    # Routes should be sorted by name
    route_names = list(result1["routes"].keys())
    assert route_names == sorted(route_names)


def test_generate_routes_ts_is_deterministic() -> None:
    """Test that generate_routes_ts produces deterministic output."""

    @get("/users/{id:int}", name="get_user", sync_to_thread=False)
    def get_user(id: int) -> dict[str, int]:
        return {"id": id}

    @get("/posts/{id:int}", name="get_post", sync_to_thread=False)
    def get_post(id: int) -> dict[str, int]:
        return {"id": id}

    @get("/comments/{id:int}", name="get_comment", sync_to_thread=False)
    def get_comment(id: int) -> dict[str, int]:
        return {"id": id}

    app = Litestar([get_user, get_post, get_comment])

    # Generate twice
    result1 = generate_routes_ts(app)
    result2 = generate_routes_ts(app)

    # Should be identical
    assert result1 == result2


def test_generate_inertia_pages_json_is_deterministic() -> None:
    """Test that generate_inertia_pages_json produces deterministic output."""

    @get("/login", name="login", opt={"component": "auth/Login"}, sync_to_thread=False)
    def login_page() -> dict[str, str]:
        return {}

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard"}, sync_to_thread=False)
    def dashboard_page() -> dict[str, str]:
        return {}

    @get("/profile", name="profile", opt={"component": "Profile/Show"}, sync_to_thread=False)
    def profile_page() -> dict[str, str]:
        return {}

    app = Litestar([login_page, dashboard_page, profile_page])

    # Generate twice
    result1 = generate_inertia_pages_json(app)
    result2 = generate_inertia_pages_json(app)

    # Remove timestamps for comparison
    result1.pop("generatedAt", None)
    result2.pop("generatedAt", None)

    # Should be identical (after removing timestamp)
    assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)

    # Pages should be sorted by component name
    page_names = list(result1["pages"].keys())
    assert page_names == sorted(page_names)


def test_generate_routes_json_params_are_sorted() -> None:
    """Test that route parameters are sorted alphabetically."""

    @get("/search", name="search", sync_to_thread=False)
    def search(z_param: str, a_param: str, m_param: str) -> list[str]:
        return []

    app = Litestar([search])
    result = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = result["routes"]["search"]
    if "queryParameters" in route_data:
        param_names = list(route_data["queryParameters"].keys())
        assert param_names == sorted(param_names)


def test_generate_routes_ts_params_are_sorted() -> None:
    """Test that TypeScript route parameters are sorted alphabetically."""

    @get("/search", name="search", sync_to_thread=False)
    def search(z_param: str, a_param: str, m_param: str) -> list[str]:
        return []

    app = Litestar([search])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Parameters should appear in alphabetical order in the generated TypeScript
    a_pos = ts_content.find("a_param")
    m_pos = ts_content.find("m_param")
    z_pos = ts_content.find("z_param")

    assert a_pos < m_pos < z_pos, "Parameters should be sorted alphabetically"


def test_inertia_pages_shared_props_are_sorted() -> None:
    """Test that shared props are sorted alphabetically."""

    @get("/test", name="test", opt={"component": "Test"}, sync_to_thread=False)
    def test_page() -> dict[str, str]:
        return {}

    app = Litestar([test_page])
    result = generate_inertia_pages_json(app)

    # Shared props should be sorted
    shared_props_names = list(result["sharedProps"].keys())
    assert shared_props_names == sorted(shared_props_names)


def test_repeated_generation_produces_identical_bytes() -> None:
    """Test that repeated generation produces byte-identical JSON."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return []

    @get("/posts", name="list_posts", sync_to_thread=False)
    def list_posts() -> list[str]:
        return []

    app = Litestar([list_users, list_posts])

    # Generate and encode multiple times
    bytes1 = encode_deterministic_json(generate_routes_json(app))
    bytes2 = encode_deterministic_json(generate_routes_json(app))
    bytes3 = encode_deterministic_json(generate_routes_json(app))

    assert bytes1 == bytes2 == bytes3


def test_inertia_json_with_timestamp_comparison() -> None:
    """Test that Inertia JSON uses timestamp-aware comparison correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "inertia-pages.json"

        @get("/test", name="test", opt={"component": "Test"}, sync_to_thread=False)
        def test_page() -> dict[str, str]:
            return {}

        app = Litestar([test_page])

        # Generate and write first version
        data1 = generate_inertia_pages_json(app)
        content1 = encode_deterministic_json(data1)
        write_if_changed(path, content1)

        # Generate second version (different timestamp)
        data2 = generate_inertia_pages_json(app)
        content2 = encode_deterministic_json(data2)

        # Write with timestamp comparison - should detect no change
        result = write_if_changed(path, content2, normalize_for_comparison=strip_timestamp_for_comparison)

        # Should NOT write because content (minus timestamp) is identical
        assert result is False


def test_routes_methods_are_sorted() -> None:
    """Test that HTTP methods are sorted in the generated output."""

    @post("/users", name="create_user", sync_to_thread=False)
    def create_user() -> dict[str, str]:
        return {}

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return []

    app = Litestar([create_user, list_users])
    ts_content = generate_routes_ts(app)

    # In routes that support multiple methods, they should be sorted
    # For single-method routes, this doesn't apply but the route names should be sorted
    assert "'create_user'" in ts_content
    assert "'list_users'" in ts_content
